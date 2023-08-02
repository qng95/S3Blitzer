import re
import os
import time
import uuid
import math
import random
import string
import logging

import boto3
from locust import task, between, User, events, SequentialTaskSet

from locust_wrapper import method_wrapper

FILE_SIZE_PATTERN = re.compile(r"(\d+)([BKMGT])")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def largest_power_of_10_less_than(X):
    power_of_10 = math.floor(math.log10(X))
    return 10 ** power_of_10


def generate_random_string(size):
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(chars) for _ in range(size))


def generate_random_text_file(filepath, file_size_bytes, chunk_size_bytes=1024):
    try:
        with open(filepath, 'w') as file:
            remaining_size = file_size_bytes
            while remaining_size > 0:
                current_chunk_size = min(chunk_size_bytes, remaining_size)
                random_string = generate_random_string(current_chunk_size)
                file.write(random_string)
                remaining_size -= current_chunk_size
    except Exception as e:
        logging.error(f"Failed to generate file {filepath}, filesize={file_size_bytes} bytes", exc_info=e)


class BotoClient:
    def __init__(self, environment, user_uuid):
        self.environment = environment
        self.user_uuid = user_uuid
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.environment.parsed_options.endpoint_url,
            aws_access_key_id=self.environment.parsed_options.access_key_id,
            aws_secret_access_key=self.environment.parsed_options.access_key_secret,
            aws_session_token=self.environment.parsed_options.session_token,
            region_name=self.environment.parsed_options.region_name
        )

    @method_wrapper(
        request_meta={
            'name': 'upload_file',
            'type': 's3'
        }
    )
    def upload_file_to_s3(self, src_file, key):
        self.s3_client.upload_file(src_file, self.environment.parsed_options.bucket_name, key)

    @method_wrapper(
        request_meta={
            'name': 'download_file',
            'type': 's3'
        }
    )
    def download_file_from_s3(self, key, dst_file):
        self.s3_client.download_file(self.environment.parsed_options.bucket_name, key, dst_file)


class S3TasksBoto3(SequentialTaskSet):

    def __init__(self, parent: "User"):
        super().__init__(parent)
        self.environment = parent.environment
        self.user_uuid = parent.uuid

        self.file_sizes = self.environment.parsed_options.file_sizes.strip()
        self.file_sizes = [size.strip() for size in self.file_sizes.split(",")]

        self.testfiles_dir = os.path.join(BASE_DIR, "testfiles")


    @task
    def upload_task(self):
        logging.info(f"Start upload task {self.user_uuid}")
        for file_size in self.file_sizes:
            file_name = f"{file_size}.txt"
            src_path = os.path.join(self.testfiles_dir, file_name)
            logging.info(f"Uploading file {src_path}")
            self.client.upload_file_to_s3(src_path, f"{file_name}.{self.user_uuid}")
        logging.info(f"Finished upload task {self.user_uuid}")

    @task
    def download_task(self):
        logging.info(f"Start download task {self.user_uuid}")
        for file_size in self.file_sizes:
            file_name = f"{file_size}.txt.{self.user_uuid}"
            dst_file = os.path.join(self.testfiles_dir, f"{file_name}.download")
            logging.info(f"downloading file {file_name}")
            self.client.download_file_from_s3(file_name, dst_file)
        logging.info(f"Finished download task {self.user_uuid}")


class S3LoadTestUser(User):
    tasks = {S3TasksBoto3}
    wait_time = between(1, 2)

    def __init__(self, environment):
        super().__init__(environment)
        self.uuid = uuid.uuid4()
        self.client = BotoClient(self.environment, self.uuid)


@events.init_command_line_parser.add_listener
def _(parser):
    # parser.add_argument("--host", type=str, default="", include_in_web_ui=False, help="")
    parser.add_argument("--region-name", type=str, default="eu-central-1",
                        help="The name of the region associated with the client")
    parser.add_argument("--endpoint-url", type=str, default="",
                        help="complete URL (including the http/https scheme)")
    parser.add_argument("--bucket-name", type=str, default="",
                        help="S3 bucket name")
    parser.add_argument("--access-key-id", type=str, default="",
                        help="AWS_ACCESS_KEY_ID")
    parser.add_argument("--access-key-secret", type=str, is_secret=True, default="",
                        help="AWS_SECRET_ACCESS_KEY")
    parser.add_argument("--session-token", type=str, is_secret=True, default="",
                        help="AWS_SESSION_TOKEN")
    parser.add_argument("--file-sizes", type=str, default="1M,10M,100M",
                        help="comma separate list offile size (\d+)([BKMGT])")


@events.test_start.add_listener
def _(environment, **kw):
    file_sizes = environment.parsed_options.file_sizes.strip()
    file_sizes = [size.strip() for size in file_sizes.split(",")]
    testfiles_dir = os.path.join(BASE_DIR, "testfiles")
    for file_size in file_sizes:
        filepath = os.path.join(testfiles_dir, f"{file_size}.txt")
        logging.info(f"Generating test file with size {file_size} at {filepath}")
        m = FILE_SIZE_PATTERN.match(file_size)
        if m:
            size_int = m.group(1)
            size_unit = m.group(2)
            size_int_bytes = int(size_int)
            chunk_size_bytes = 1
            match size_unit:
                case "B":
                    chunk_size_bytes = 1
                case "K":
                    chunk_size_bytes = 1024
                case "M":
                    chunk_size_bytes = 1024 * 1024
                case "G":
                    chunk_size_bytes = 1024 * 1024 * 1024
                case "T":
                    chunk_size_bytes = 1024 * 1024 * 1024 * 1024

            size_int_bytes *= chunk_size_bytes
            pow = largest_power_of_10_less_than(size_int_bytes)

            # if file exist and only less than few bytes as expected then skip creation
            if os.path.exists(filepath):
                current_size = os.stat(filepath).st_size
                if abs(current_size-size_int_bytes) <= 100:
                    logging.info(f"File with size {file_size} already exists at {filepath}")
                    continue

            generate_random_text_file(filepath, size_int_bytes, pow*chunk_size_bytes)


@events.test_stop.add_listener
def _(environment, **kw):
    pass
