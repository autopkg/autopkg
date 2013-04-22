#!/usr/bin/env python
#
# Copyright 2011 Per Olofsson
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


import os.path
import shutil

from autopkglib import Processor, ProcessorError


__all__ = ["FileCreator"]


class FileCreator(Processor):
    description = "Create a file."
    # FIXME: add mode, owner
    input_variables = {
        "file_path": {
            "required": True,
            "description": "Path to a file to create.",
        },
        "file_content": {
            "required": True,
            "description": "Contents to put in file.",
        },
    }
    output_variables = {
    }
    
    __doc__ = description
    
    def main(self):
        try:
            with open(self.env['file_path'], "w") as f:
                f.write(self.env['file_content'])
            self.output("Created file at %s" % self.env['file_path'])
        except BaseException as e:
            raise ProcessorError("Can't create file at %s: %s" % (
                                  self.env['file_path'],
                                  e))
    

if __name__ == '__main__':
    processor = FileCreator()
    processor.execute_shell()
    
