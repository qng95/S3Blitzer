import os
import time
import tomllib
import logging
import argparse
import subprocess
from typing import Dict

import jinja2

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)


class CommandExecutor:
    def __init__(self, verbose=False, dry_run=False):
        self.verbose = verbose
        self.dry_run = dry_run

    def execute(self, args, cwd: str = None, input: str = None, env: Dict[str, str] = None, background: bool = False):
        logging.info(f"Executing command:"
                     f"\ncwd = '{cwd}'"
                     f"\ninput = '{input}'"
                     f"\nenv = {env}"
                     f"\nbackground = '{background}'"
                     f"\ncommand = '{' '.join(args)}'"
                     "\n")

        if not self.dry_run:
            starttime = time.time()
            if background:
                proc = subprocess.Popen(args, cwd=cwd, env=env, stdin=subprocess.PIPE, start_new_session=True)
                proc.stdin.write(input)
                proc.stdin.flush()
                proc.stdin.close()
            else:
                proc = subprocess.run(args, cwd=cwd, input=input, env=env, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
                stdout = proc.stdout.decode("utf-8", "ignore")
                stderr = proc.stderr.decode("utf-8", "ignore")

                if stdout.strip():
                    logging.info(f"Command stdout:\n{stdout}\n")
                if stderr.strip():
                    logging.info(f"Command stderr:\n{stderr}\n")

                logging.info(f"Command returncode={proc.returncode} , execution_time={time.time() - starttime}\n")


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
        "-auto-approve"
    ]
    # TODO: dynamic CWD, for now we only have aws+eks
    cwd = os.path.join(BASE_DIR, "terraform", "aws_eks")
    command_executor.execute(args=args, cwd=cwd)

    args = [
        "terraform",
        "apply",
        "-auto-approve"
    ]
    cwd = os.path.join(BASE_DIR, "terraform", "aws_eks")
    command_executor.execute(args=args, cwd=cwd)

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
    command_executor.execute(args=args, cwd=cwd)

    # apply kubernetes
    args = [
        "kubectl",
        "config",
        f"--kubeconfig={os.path.join(BASE_DIR, 'kubeconfig')}",
    ]
    cwd = os.path.join(BASE_DIR)
    command_executor.execute(args=args, cwd=cwd)

    args = [
        "kubectl",
        "apply",
        "-R",
        f"-f={os.path.join(BASE_DIR, 'kubernetes')}/"
    ]
    cwd = os.path.join(BASE_DIR, "kubernetes")
    command_executor.execute(args=args, cwd=cwd)


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
    command_executor.execute(args=args, cwd=cwd)

    # apply kubernetes
    args = [
        "kubectl",
        "config",
        f"--kubeconfig={os.path.join(BASE_DIR, 'kubeconfig')}",
    ]
    cwd = os.path.join(BASE_DIR)
    command_executor.execute(args=args, cwd=cwd)

    args = [
        "kubectl",
        "delete",
        "-R",
        f"-f={os.path.join(BASE_DIR, 'kubernetes')}/"
    ]
    cwd = os.path.join(BASE_DIR, "kubernetes")
    command_executor.execute(args=args, cwd=cwd)

    # init and apply terraform
    args = [
        "terraform",
        "init",
        "-auto-approve"
    ]
    # TODO: dynamic CWD, for now we only have aws+eks
    cwd = os.path.join(BASE_DIR, "terraform", "aws_eks")
    command_executor.execute(args=args, cwd=cwd)

    args = [
        "terraform",
        "destroy",
        "-auto-approve"
    ]
    cwd = os.path.join(BASE_DIR, "terraform", "aws_eks")
    command_executor.execute(args=args, cwd=cwd)


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
