#!/usr/local/autopkg/python
#
# Copyright 2010 Per Olofsson
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
"""See docstring for FolderCreator class"""

import os.path
import shutil

from autopkglib.PkgRootCreator import PkgRootCreator

__all__ = ["FolderCreator"]

class FolderCreator(PkgRootCreator):
    """Create a directory and relative subdirectories and set their permissions."""

    description = __doc__
    input_variables = {
        "root": {
            "required": True,
            "description": "Path to where the root folder will be created.",
        },
        "subdirs": {
            "required": False,
            "description": (
                "A dictionary of directories to be created "
                "inside the root, with their modes in octal form."
            ),
        },
    }
    output_variables = {}

    def main(self):
        root = self.env['root']
        if 'subdirs' not in self.env:
            subdirs = {}
        else:
            subdirs = self.env['subdirs']
        # calls create on PkgRootCreator class
        self.Create(root, subdirs)

if __name__ == "__main__":
    PROCESSOR = FolderCreator()
    PROCESSOR.execute_shell()
