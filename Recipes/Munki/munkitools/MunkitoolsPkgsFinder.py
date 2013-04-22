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


import os
import glob

from autopkglib.DmgMounter import DmgMounter
from autopkglib import Processor, ProcessorError


__all__ = ["MunkitoolsPkgsFinder"]

CORE = "*.mpkg/Contents/Packages/munkitools_core*.pkg"
ADMIN = "*.mpkg/Contents/Packages/munkitools_admin*.pkg"
APP = "*.mpkg/Contents/Packages/munkitools_app*.pkg"
LAUNCHD = "*.mpkg/Contents/Packages/munkitools_launchd*.pkg"


class MunkitoolsPkgsFinder(DmgMounter):
    """Mounts a munkitools dmg and finds the sub packages."""
    input_variables = {
        "dmg_path": {
            "required": True,
            "description": "Path to a dmg containing the munkitools mpkg.",
        },
    }
    output_variables = {
        "munki_core_pkg": {
            "description": "Relative path to munkitools_core.pkg.",
        },
        "munki_admin_pkg": {
            "description": "Relative path to munkitools_admin.pkg.",
        },
        "munki_app_pkg": {
            "description": "Relative path to munkitools_app.pkg.",
        },
        "munki_launchd_pkg": {
            "description": "Relative path to munkitools_launchd.pkg.",
        },
    }
    description = __doc__
    
    def find_match(self, mount_point, match_string):
        """Finds a file using shell globbing"""
        matches = glob.glob(os.path.join(mount_point, match_string))
        if matches:
            return matches[0][len(mount_point) + 1:]
        else:
            return ""
    
    def main(self):
        # Mount the image.
        mount_point = self.mount(self.env["dmg_path"])
        # Wrap all other actions in a try/finally so the image is always
        # unmounted.
        try:
            self.env["munki_core_pkg"] = self.find_match(mount_point, CORE)
            self.output("Found %s" % self.env["munki_core_pkg"])
            self.env["munki_admin_pkg"] = self.find_match(mount_point, ADMIN)
            self.output("Found %s" % self.env["munki_admin_pkg"])
            self.env["munki_app_pkg"] = self.find_match(mount_point, APP)
            self.output("Found %s" % self.env["munki_app_pkg"])
            self.env["munki_launchd_pkg"] = self.find_match(
                mount_point, LAUNCHD)
            self.output("Found %s" % self.env["munki_launchd_pkg"])
        except BaseException as err:
            raise ProcessorError(err)
        finally:
            self.unmount(self.env["dmg_path"])
        
        
if __name__ == "__main__":
    processor = MunkitoolsPkgsFinder()
    processor.execute_shell()
