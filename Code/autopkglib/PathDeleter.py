#!/usr/bin/env python
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


from autopkglib import Processor, ProcessorError
import shutil
import os


__all__ = ["PathDeleter"]


class PathDeleter(Processor):
    """Deletes file paths."""
    input_variables = {
        "path_list": {
            "required": True,
            "description": 
                "List of pathnames to be deleted",
        },
    }
    output_variables = {
    }
    description = __doc__
    
    def main(self):
        for path in self.env["path_list"]:
            try:
                if os.path.isfile(path) or os.path.islink(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                elif not os.path.exists(path):
                    raise ProcessorError(
                        "Could not remove %s - it does not exist!" % path)
                else:
                    raise ProcessorError(
                        "Could not remove %s - it is not a file, link, "
                        "or directory" % path)
                self.output("Deleted %s" % path)
            except OSError, err:
                raise ProcessorError(
                    "Could not remove %s: %s" % (path, err))


if __name__ == "__main__":
    processor = PathDeleter()
    processor.execute_shell()
