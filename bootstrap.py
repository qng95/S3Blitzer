import os
import time
import tomllib
import logging
import argparse
import threading
import subprocess
from typing import Dict

import jinja2

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)


class CommandExecutor:
    def __init__(self, verbose=False, dry_run=False):
        self.verbose = verbose
        self.dry_run = dry_run

    def execute(self, args, cwd: str = None, env: Dict[str, str] = None):
        logging.info(f"Executing command:"
                     f"\ncwd = '{cwd}'"
                     f"\nenv = {env}"
                     f"\ncommand = '{' '.join(args)}'"
                     "\n")

        def read_stream(stream, callback):
            for line in stream:
                callback(line.decode().strip())

        if not self.dry_run:
            starttime = time.time()
            proc = subprocess.Popen(args, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            stdout_thread = threading.Thread(target=read_stream,
                                             args=(proc.stdout, lambda line: logging.info(f"STDOUT: {line}")))
            stderr_thread = threading.Thread(target=read_stream,
                                             args=(proc.stderr, lambda line: logging.info(f"STDERR: {line}")))

            stdout_thread.start()
            stderr_thread.start()

            # Wait for the process to complete and threads to finish
            proc.wait()
            stdout_thread.join()
            stderr_thread.join()

            logging.info(f"Command returncode={proc.returncode} , execution_time={time.time() - starttime}\n")

            return proc.returncode
        else:
            return 0


class Config:
    DEFAULT_CONFIG_FILE = os.path.join(BASE_DIR, "config.toml")

    def __init__(self, config_file=None, dry_run=False, verbose=False):
        self.dry_run = dry_run
        self.verbose = verbose
        if config_file:
            self.config_file = config_file
        else:
            self.config_file = self.DEFAULT_CONFIG_FILE
        self.config = None
        self.__init_config()
        self.__template()

    def __init_config(self):
        logging.info(f"Initializing config data from {self.config_file}\n")
        with open(self.config_file, "rb") as f:
            self.config = tomllib.load(f)

    def __template(self):
        logging.info(f"Templating all .jinja2 config file with config data\n")
        jinja_env = jinja2.Environment()
        for root, _, files in os.walk(BASE_DIR):
            for file in files:
                if file.endswith(".jinja2"):
                    fpath = os.path.join(root, file)

                    if self.verbose:
                        logging.debug(f"Templating {fpath}\n")

                    with open(fpath, 'r') as f:
                        content = f.read()
                        template = jinja_env.from_string(content)
                        output = template.render(self.config)

                    if output:
                        with open(fpath.replace(".jinja2", ""), "w") as f:
                            f.write(output)


def deploy(cfg: Config, command_executor: CommandExecutor):
    # init and apply terraform
    args = [
        "terraform",
        "init",
    ]
    # TODO: dynamic CWD, for now we only have aws+eks
    cwd = os.path.join(BASE_DIR, "terraform", "aws_eks")
    exit_code = command_executor.execute(args=args, cwd=cwd)
    if exit_code != 0:
        if os.path.exists(os.path.join(cwd, '.terraform')):
            logging.error("Failed to init terraform directory.")
        else:
            raise Exception("Failed to init terraform")

    args = [
        "terraform",
        "apply",
        "-auto-approve"
    ]
    cwd = os.path.join(BASE_DIR, "terraform", "aws_eks")
    exit_code = command_executor.execute(args=args, cwd=cwd)
    if exit_code != 0:
        raise Exception("Failed to apply terraform manifest")

    # fetch kubeconfig
    args = [
        "aws",
        "eks",
        "--region",
        f"{cfg.config['aws']['target_region']}",
        "update-kubeconfig",
        "--name",
        f"{cfg.config['aws']['cluster_name']}",
        "--kubeconfig",
        f"{os.path.join(BASE_DIR, 'kubeconfig')}",
    ]
    cwd = os.path.join(BASE_DIR)
    exit_code = command_executor.execute(args=args, cwd=cwd)
    if exit_code != 0:
        if os.path.exists(os.path.join(BASE_DIR, 'kubeconfig')):
            logging.warning(
                f"Failed to create kubeconfig file, will reuse old file at {os.path.join(BASE_DIR, 'kubeconfig')}")
        else:
            raise Exception(f"Failed to create kubeconfig file at {os.path.join(BASE_DIR, 'kubeconfig')}")

    # deploy docker registry credential as secrets
    dockerconfigjson = cfg.config['docker']['dockerconfigjson']
    if dockerconfigjson and os.path.exists(dockerconfigjson):
        args = [
            "kubectl",
            f"--kubeconfig={os.path.join(BASE_DIR, 'kubeconfig')}",
            "create",
            "secret",
            "generic",
            "regcred",
            f"--from-file=.dockerconfigjson={cfg.config['docker']['dockerconfigjson']}",
            f"--type=kubernetes.io/dockerconfigjson",
        ]
        cwd = os.path.join(BASE_DIR)
        exit_code = command_executor.execute(args=args, cwd=cwd)
        if exit_code != 0:
            raise Exception(f"Failed to create docker registry credentials as Secrets")
    else:
        logging.warning(f"dockerconfigjson is not configured or not exists at path {dockerconfigjson}. "
                        f"Make sure that the configured docker image can be pull without authentication required.")

    args = [
        "kubectl",
        f"--kubeconfig={os.path.join(BASE_DIR, 'kubeconfig')}",
        "apply",
        "-R",
        f"-f={os.path.join(BASE_DIR, 'kubernetes')}/"
    ]
    cwd = os.path.join(BASE_DIR, "kubernetes")
    exit_code = command_executor.execute(args=args, cwd=cwd)
    if exit_code != 0:
        raise Exception("Failed to create kubernetes resources")

    args = [
        "kubectl",
        f"--kubeconfig={os.path.join(BASE_DIR, 'kubeconfig')}",
        "get",
        "service",
        "locust-master-public",
        "--output=jsonpath=\"http://{.status.loadBalancer.ingress[0].hostname}:{.spec.ports[0].port}\""
    ]
    cwd = os.path.join(BASE_DIR, "kubernetes")
    exit_code = command_executor.execute(args=args, cwd=cwd)
    if exit_code != 0:
        logging.error("Failed to fetch public URL for the locust Service")


def destroy(cfg: Config, command_executor: CommandExecutor):
    # fetch kubeconfig
    args = [
        "aws",
        "eks",
        "--region",
        f"{cfg.config['aws']['target_region']}",
        "update-kubeconfig",
        "--name",
        f"{cfg.config['aws']['cluster_name']}",
        "--kubeconfig",
        f"{os.path.join(BASE_DIR, 'kubeconfig')}",
    ]
    cwd = os.path.join(BASE_DIR)
    exit_code = command_executor.execute(args=args, cwd=cwd)
    if exit_code != 0:
        if os.path.exists(os.path.join(BASE_DIR, 'kubeconfig')):
            logging.warning(
                f"Failed to create kubeconfig file, will reuse old file at {os.path.join(BASE_DIR, 'kubeconfig')}")
        else:
            raise Exception(f"Failed to create kubeconfig file at {os.path.join(BASE_DIR, 'kubeconfig')}")

    args = [
        "kubectl",
        f"--kubeconfig={os.path.join(BASE_DIR, 'kubeconfig')}",
        "delete",
        "-R",
        f"-f={os.path.join(BASE_DIR, 'kubernetes')}/"
    ]
    cwd = os.path.join(BASE_DIR, "kubernetes")
    exit_code = command_executor.execute(args=args, cwd=cwd)
    if exit_code != 0:
        logging.error(f"Failed to delete kubernetes resources")

    args = [
        "kubectl",
        f"--kubeconfig={os.path.join(BASE_DIR, 'kubeconfig')}",
        "delete",
        "secret/regcred",
    ]
    cwd = os.path.join(BASE_DIR, "kubernetes")
    exit_code = command_executor.execute(args=args, cwd=cwd)
    if exit_code != 0:
        logging.error(f"Failed to delete docker registry credentials Secrets")

    # init and apply terraform
    args = [
        "terraform",
        "init",
    ]
    # TODO: dynamic CWD, for now we only have aws+eks
    cwd = os.path.join(BASE_DIR, "terraform", "aws_eks")
    exit_code = command_executor.execute(args=args, cwd=cwd)
    if exit_code != 0:
        if os.path.exists(os.path.join(cwd, '.terraform')):
            logging.error("Failed to init terraform directory.")
        else:
            raise Exception("Failed to init terraform")

    args = [
        "terraform",
        "destroy",
        "-auto-approve"
    ]
    cwd = os.path.join(BASE_DIR, "terraform", "aws_eks")
    exit_code = command_executor.execute(args=args, cwd=cwd)
    if exit_code != 0:
        raise Exception(f"Failed to destroy resources")


def main():
    parser = argparse.ArgumentParser("S3Blitzer bootstrapping")
    parser.add_argument("command", choices=["deploy", "destroy", "template"], type=str, help="command to execute")
    parser.add_argument("-d", "--dry-run", action="store_true", help="don't execute just log the what will be done")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose debug output")
    parser.add_argument("-c", "--config-file", help="specified different config file")

    args = parser.parse_args()
    command = args.command

    try:
        config = Config(config_file=args.config_file, dry_run=args.dry_run, verbose=args.verbose)
        if config.verbose:
            logging.getLogger('root').setLevel('DEBUG')
        else:
            logging.getLogger('root').setLevel('INFO')
        command_executor = CommandExecutor(verbose=config.verbose, dry_run=config.dry_run)
        match command:
            case 'deploy':
                deploy(config, command_executor)
            case 'destroy':
                destroy(config, command_executor)
            case 'template':
                # does nothing
                pass
            case _:
                parser.print_help()
    except Exception as e:
        parser.print_help()
        logging.error(f"Failed to run command {command}", exc_info=e)


if __name__ == '__main__':
    main()
