#!/usr/local/autopkg/python
#
# Copyright 2024 Dennis Henry @dennishenry
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""See docstring for S3Downloader class"""

import boto3
from autopkglib import Processor, ProcessorError

__all__ = ["S3Downloader"]

class S3Downloader(Processor):
    """Downloads a file from S3 after assuming an IAM role.
    
    Takes in a aws_role_arn, aws_role_session_name, s3_bucket_name, 
    s3_object_key, and download_path. aws_role_session_name is 
    optional and defaults to 'S3DownloaderSession'.
    """
    description = __doc__
    input_variables = {
        "aws_role_arn": {
            "required": True,
            "description": "The ARN of the AWS IAM role to assume."
        },
        "aws_role_session_name": {
            "required": False,
            "description": "An identifier for the assumed role session."
        },
        "s3_bucket_name": {
            "required": True,
            "description": "The name of the S3 bucket."
        },
        "s3_object_key": {
            "required": True,
            "description": "The key (path) of the S3 object."
        },
        "download_path": {
            "required": True,
            "description": "The local path where the file will be downloaded."
        },
    }
    output_variables = {}

    def main(self):
        aws_role_arn = self.env.get("aws_role_arn")
        aws_role_session_name = self.env.get("aws_role_session_name", "S3DownloaderSession")
        s3_bucket_name = self.env.get("s3_bucket_name")
        s3_object_key = self.env.get("s3_object_key")
        download_path = self.env.get("download_path")

        # Assume the IAM role
        sts_client = boto3.client('sts')
        try:
            assumed_role = sts_client.assume_role(
                RoleArn=aws_role_arn,
                RoleSessionName=aws_role_session_name
            )
        except Exception as e:
            raise ProcessorError(f"Failed to assume role: {e}")

        credentials = assumed_role['Credentials']

        # Create an S3 client using the temporary credentials
        s3_client = boto3.client(
            's3',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
        )

        # Download the file
        try:
            s3_client.download_file(s3_bucket_name, s3_object_key, download_path)
        except Exception as e:
            raise ProcessorError(f"Failed to download file from S3: {e}")


if __name__ == "__main__":
    PROCESSOR = S3Downloader()
    PROCESSOR.execute_shell()
