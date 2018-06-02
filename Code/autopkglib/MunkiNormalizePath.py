#!/usr/bin/env python
#
# Copyright 2018 Yoann Gini
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
"""See docstring for MunkiNormalizePath class"""

from autopkglib import Processor
import re 

__all__ = ["MunkiNormalizePath"]


class MunkiNormalizePath(Processor):
    """Edit current munki pkginfo to normalize the 'MUNKI_REPO_SUBDIR' and 'NAME'
    to replace spaces with underscore and ensure everything is lowercase.
    Typically this would be run as a preprocessor."""
    input_variables = {
        "MUNKI_REPO_SUBDIR": {
            "required": True,
            "description": "The target munki subdirectory",
        },
        "NAME": {
            "required": True,
            "description": "The target package name",
        }
    }
    output_variables = {
        "MUNKI_REPO_SUBDIR": {
            "description": "The updated target munki subdirectory",
        },
        "NAME": {
            "description": "The updated target package name",
        }
    }
    description = __doc__

    def main(self):
        if "pkginfo" not in self.env:
            self.env["pkginfo"] = {}
        original_name = self.env["NAME"]
        original_subdir = self.env["MUNKI_REPO_SUBDIR"]
        if original_name:
            self.env["NAME"] = re.sub('[^0-9a-zA-Z/]+', '_', original_name.lower())
            self.output("Updated NAME with %s"
                        % self.env["NAME"])
        if original_subdir:
            self.env["MUNKI_REPO_SUBDIR"] = re.sub('[^0-9a-zA-Z/]+', '_', original_subdir.lower())
            self.output("Updated MUNKI_REPO_SUBDIR with %s"
                        % self.env["MUNKI_REPO_SUBDIR"])

if __name__ == "__main__":
    PROCESSOR = MunkiNormalizePath()
    PROCESSOR.execute_shell()
