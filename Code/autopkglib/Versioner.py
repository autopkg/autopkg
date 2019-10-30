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
"""See docstring for Versioner class"""

import os.path
import plistlib

from autopkglib import ProcessorError
from autopkglib.DmgMounter import DmgMounter

__all__ = ["Versioner"]


class Versioner(DmgMounter):
    """Returns version information from a plist"""

    description = __doc__

    input_variables = {
        "input_plist_path": {
            "required": True,
            "description": (
                "File path to a plist. Can point to a path inside a .dmg "
                "which will be mounted."
            ),
        },
        "plist_version_key": {
            "required": False,
            "default": "CFBundleShortVersionString",
            "description": (
                "Which plist key to use; defaults to " "CFBundleShortVersionString"
            ),
        },
    }
    output_variables = {"version": {"description": "Version of the item."}}

    def main(self):
        """Return a version for file at input_plist_path"""
        # Check if we're trying to read something inside a dmg.
        (dmg_path, dmg, dmg_source_path) = self.parsePathForDMG(
            self.env["input_plist_path"]
        )
        try:
            if dmg:
                # Mount dmg and copy path inside.
                mount_point = self.mount(dmg_path)
                input_plist_path = os.path.join(mount_point, dmg_source_path)
            else:
                # just use the given path
                input_plist_path = self.env["input_plist_path"]
            if not os.path.exists(input_plist_path):
                raise ProcessorError(
                    "File '%s' does not exist or could not be read." % input_plist_path
                )
            try:
                with open(input_plist_path, "rb") as f:
                    plist = plistlib.load(f)
                version_key = self.env.get("plist_version_key")
                self.env["version"] = plist.get(version_key, "UNKNOWN_VERSION")
                self.output(
                    "Found version %s in file %s"
                    % (self.env["version"], input_plist_path)
                )
            except Exception as err:
                raise ProcessorError(err)

        finally:
            if dmg:
                self.unmount(dmg_path)


if __name__ == "__main__":
    PROCESSOR = Versioner()
    PROCESSOR.execute_shell()
