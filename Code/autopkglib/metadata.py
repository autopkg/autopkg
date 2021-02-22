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

from autopkglib import BUNDLE_ID

class Metadata:
    def __init__(self, json_object):
        self.json_object = json_object
        try:
            with open(self.json_object, "rb") as json_file:
                self.json_data = json.load(json_file)
        except:
            self.json_data = dict()
    
    def getmetadata(self, filename, metadata):
        try:
            return self.json_data.get(filename).get(metadata)
        except AttributeError:
            return None
    def setmetadata(self, filename, metadata, value):
        try:
            self.json_data[filename][metadata] = value
        except KeyError:
            self.json_data[filename] = dict()
            self.json_data[filename][metadata] = value
        with open(self.json_object, "w") as json_file:
            json.dump(self.json_data, json_file)
