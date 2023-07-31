import os
import time

import boto3
from locust import TaskSet, task, between, User

import _configs as cfg
from locust_wrapper import method_wrapper


class BotoClient:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=cfg.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=cfg.AWS_SECRET_ACCESS_KEY,
            region_name=cfg.AWS_REGION_NAME
        )

    @method_wrapper(
        request_meta={
            'name': 'upload_file',
            'type': 's3'
        }
    )
    def upload_file_to_s3(self, file_path, key_name):
        self.s3_client.upload_file(file_path, cfg.BUCKET_NAME, key_name)


class S3TasksBoto3(TaskSet):
    @task
    def upload_task(self):
        print("Hello Upload Task")
        file_name = 'test_file.txt'
        file_content = 'This is a test file content.'
        file_path = '/tmp/' + file_name

        with open(file_path, 'w') as file:
            file.write(file_content)

        self.client.upload_file_to_s3(file_path, file_name)
        os.remove(file_path)


class S3LoadTestUser(User):
    tasks = {S3TasksBoto3}
    wait_time = between(1, 5)

    def __init__(self, env):
        super().__init__(env)
        self.client = BotoClient()
