#!/usr/bin/python
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
"""See docstring for AppDmgVersioner class"""

import os.path
import glob
import FoundationPlist

from autopkglib.DmgMounter import DmgMounter
from autopkglib import ProcessorError


__all__ = ["AppDmgVersioner"]


class AppDmgVersioner(DmgMounter):
    # we dynamically set the docstring from the description (DRY), so:
    #pylint: disable=missing-docstring
    description = "Extracts bundle ID and version of app inside dmg."
    input_variables = {
        "dmg_path": {
            "required": True,
            "description": "Path to a dmg containing an app.",
        },
        "plist_version_key": {
            "required": False,
            "default": "CFBundleShortVersionString",
            "description":
                ("Which plist key to use; defaults to "
                 "CFBundleShortVersionString"),
        },
    }
    output_variables = {
        "app_name": {
            "description": "Name of app found on the disk image."
        },
        "bundleid": {
            "description": "Bundle identifier of the app.",
        },
        "version": {
            "description": "Version of the app.",
        },
    }

    __doc__ = description


    def find_app(self, path):
        """Find app bundle at path."""
        #pylint: disable=no-self-use
        apps = glob.glob(os.path.join(path, "*.app"))
        if len(apps) == 0:
            raise ProcessorError("No app found in dmg")
        return apps[0]


    def main(self):
        # Mount the image.
        mount_point = self.mount(self.env["dmg_path"])
        # Wrap all other actions in a try/finally so the image is always
        # unmounted.
        try:
            app_path = self.find_app(mount_point)
            plist_path = os.path.join(app_path, 'Contents', 'Info.plist')
            info = FoundationPlist.readPlist(plist_path)
            self.env["app_name"] = os.path.basename(app_path)
            try:
                self.env["bundleid"] = info["CFBundleIdentifier"]
                self.env["version"] = info[self.env["plist_version_key"]]
                self.output("BundleID: %s" % self.env["bundleid"])
                self.output("Version: %s" % self.env["version"])
            except BaseException as err:
                raise ProcessorError(err)
        finally:
            self.unmount(self.env["dmg_path"])


if __name__ == '__main__':
    PROCESSOR = AppDmgVersioner()
    PROCESSOR.execute_shell()

