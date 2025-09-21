#!/usr/local/autopkg/python
#
# Copyright 2014 Jesse Peterson
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
"""See docstring for FileMover class"""

from os import rename

from autopkglib import Processor

__all__ = ["FileMover"]


class FileMover(Processor):
    """Moves/renames a file.

    Requires version 0.2.9."""

    input_variables = {
        "source": {
            "required": True,
            "description": "Full path to the file to be moved or renamed.",
        },
        "target": {
            "required": True,
            "description": "Full path where the file should be moved to.",
        },
    }
    output_variables = {}

    description = __doc__

    def main(self) -> None:
        rename(self.env["source"], self.env["target"])
        self.output(f"File {self.env['source']} moved to {self.env['target']}")


if __name__ == "__main__":
    PROCESSOR = FileMover()
    PROCESSOR.execute_shell()
