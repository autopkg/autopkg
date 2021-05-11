#!/usr/local/autopkg/python
#
# Copyright 2013 Jesse Peterson
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
"""See docstring for FileFinder class"""


import os.path
from glob import glob

from autopkglib import ProcessorError
from autopkglib.DmgMounter import DmgMounter

__all__ = ["FileFinder"]


class FileFinder(DmgMounter):
    """Finds a filename for use in other Processors.

    Currently only supports glob filename patterns.

    Requires version 0.2.3.
    """

    input_variables = {
        "pattern": {
            "description": "Shell glob pattern to match files by",
            "required": True,
        },
        "find_method": {
            "description": (
                "Type of pattern to match. Currently only "
                'supported type is "glob" (also the default)'
            ),
            "default": "glob",
            "required": False,
        },
    }
    output_variables = {
        "found_filename": {"description": "Full path of found filename"},
        "dmg_found_filename": {"description": "DMG-relative path of found filename"},
        "found_basename": {"description": "Basename of found filename"},
    }

    description = __doc__

    def globfind(self, pattern):
        """If multiple files are found the last alphanumerically sorted found
        file is returned"""

        glob_matches = glob(pattern, recursive=True)

        if len(glob_matches) < 1:
            raise ProcessorError("No matching filename found")

        glob_matches.sort()

        return glob_matches[-1]

    def main(self):
        pattern = self.env.get("pattern")

        method = self.env.get("find_method")

        if method != "glob":
            raise ProcessorError(f"Unsupported find_method: {method}")

        source_path = pattern

        # Check if we're trying to copy something inside a dmg.
        (dmg_path, dmg, dmg_source_path) = self.parsePathForDMG(source_path)
        try:
            if dmg:
                # Mount dmg and copy path inside.
                mount_point = self.mount(dmg_path)
                source_path = os.path.join(mount_point, dmg_source_path)
            # process path with globbing
            match = self.globfind(source_path)
            self.env["found_filename"] = match
            self.output(
                f"Found file match: '{self.env['found_filename']}' from globbed '{source_path}'"
            )

            if dmg and match.startswith(mount_point):
                self.env["dmg_found_filename"] = match[len(mount_point) :].lstrip("/")
                self.output(
                    f"DMG-relative file match: '{self.env['dmg_found_filename']}'"
                )

            if match.endswith('/'):
                self.env["found_basename"] = os.path.basename(match.rstrip("/"))
            else:
                self.env["found_basename"] = os.path.basename(match)
            self.output(
                f"Basename match: '{self.env['found_basename']}'"
            )

        finally:
            if dmg:
                self.unmount(dmg_path)


if __name__ == "__main__":
    PROCESSOR = FileFinder()
    PROCESSOR.execute_shell()
