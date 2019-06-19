#!/usr/bin/python
#
# Copyright 2019 Andy Duss
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

from os import mkdir

from autopkglib import Processor

__all__ = ["DirectoryCreator"]


class DirectoryCreator(Processor):
    """Creates a new directory"""

    description = "Creates a new directory"
    input_variables = {
        "path": {
            "description": "Source file",
            "required": True}
    }
    output_variables = {}

    def main(self):
        mkdir(self.env['path'])
        self.output('Created %s' % self.env['path'])


if __name__ == "__main__":
    PROCESSOR = DirectoryCreator()
    PROCESSOR.execute_shell()
