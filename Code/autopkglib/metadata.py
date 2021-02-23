#!/usr/local/autopkg/python
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
"""
Module that provides a way to read data from a json object
"""
import json
import redis

from redis.exceptions import ConnectionError, ResponseError
from autopkglib import log_err


class Metadata:
    def __init__(self, external_metadata):
        print(external_metadata)
        self.metadata_object = None
        self.host = external_metadata.get("host")
        self.port = external_metadata.get("port")
        self.db = external_metadata.get("db")
        self.path = external_metadata.get("path")
        if (
            self.host and
            self.port and
            self.db or
            self.db == 0
        ):
            try:
                self.metadata_object = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db
                )
                self.metadata_object.ping()
                self.metadata = self.metadata_object
            except ConnectionError as err:
                log_err(f"Error connecting to redis db: {err}")
                raise
            except ResponseError as err:
                log_err(f"Error connecting to redis db: {err}")
                raise
        if not isinstance(
            self.metadata_object, redis.client.Redis
            ) and self.path:
            try:
                with open(self.path, "rb") as json_file:
                    self.metadata = json.load(json_file)
            except:
                self.metadata = dict()
    
    def getmetadata(self, filename, attribute):
        if not isinstance(self.metadata_object, redis.client.Redis):
            try:
                return self.metadata.get(filename).get(attribute)
            except AttributeError:
                return None
        try:
            return self.metadata.hget(filename, attribute).decode()
        except AttributeError:
            return None

    def setmetadata(self, filename, attribute, value):
        if not isinstance(
            self.metadata_object, redis.client.Redis
            ) and self.path:
            try:
                self.metadata[filename][attribute] = value
            except KeyError:
                self.metadata[filename] = dict()
                self.metadata[filename][attribute] = value
            with open(self.path, "w") as json_file:
                json.dump(self.metadata, json_file)
            return
        self.metadata.hset(filename, attribute, value)
        return
