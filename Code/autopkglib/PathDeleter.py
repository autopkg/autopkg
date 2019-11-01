#!/Library/AutoPkg/Python3/Python.framework/Versions/Current/bin/python3
#
# Copyright 2013 Greg Neagle
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
"""See docstring for PathDeleter class"""

import os
import shutil

from autopkglib import Processor, ProcessorError

__all__ = ["PathDeleter"]


class PathDeleter(Processor):
    """Deletes file paths."""

    input_variables = {
        "path_list": {
            "required": True,
            "description": (
                "An array or list of pathnames to be deleted, "
                "even if that list contains a single item."
            ),
        }
    }
    output_variables = {}
    description = __doc__

    def main(self):
        # if recipe writer gave us a single string instead of a list of strings,
        # convert it to a list of strings
        if isinstance(self.env["path_list"], str):
            self.env["path_list"] = [self.env["path_list"]]

        for path in self.env["path_list"]:
            try:
                if os.path.isfile(path) or os.path.islink(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                elif not os.path.exists(path):
                    raise ProcessorError(
                        f"Could not remove {path} - it does not exist!"
                    )
                else:
                    raise ProcessorError(
                        f"Could not remove {path} - it is not a file, link, "
                        "or directory"
                    )
                self.output(f"Deleted {path}")
            except OSError as err:
                raise ProcessorError(f"Could not remove {path}: {err}")


if __name__ == "__main__":
    PROCESSOR = PathDeleter()
    PROCESSOR.execute_shell()
