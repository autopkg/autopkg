#!/usr/local/autopkg/python
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
"""Processor that creates a file"""

import os

from autopkglib import Processor, ProcessorError

__all__ = ["FileCreator"]


class FileCreator(Processor):
    """Create a file."""

    description = __doc__
    input_variables = {
        "file_path": {"required": True, "description": "Path to a file to create."},
        "file_content": {"required": True, "description": "Contents to put in file."},
        "file_mode": {
            "required": False,
            "description": "String. Numeric mode for file in octal format.",
        },
    }
    output_variables = {}

    def main(self):
        try:
            with open(self.env["file_path"], "w") as fileref:
                fileref.write(self.env["file_content"])
            self.output(f"Created file at {self.env['file_path']}")
        except BaseException as err:
            raise ProcessorError(
                f"Can't create file at {self.env['file_path']}: {err}"
            ) from err
        if "file_mode" in self.env:
            try:
                os.chmod(self.env["file_path"], int(self.env["file_mode"], 8))
            except BaseException as err:
                raise ProcessorError(
                    f"Can't set mode of {self.env['file_path']} to "
                    f"{self.env['file_mode']}: {err}"
                ) from err


if __name__ == "__main__":
    PROCESSOR = FileCreator()
    PROCESSOR.execute_shell()
