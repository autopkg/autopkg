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

from __future__ import print_function

import glob
import os.path

from autopkglib import ProcessorError
from autopkglib.DmgMounter import DmgMounter

#pylint: disable=no-name-in-module
try:
    from Foundation import NSData, NSPropertyListSerialization
    from Foundation import NSPropertyListMutableContainers
except:
    print(
        "WARNING: Failed 'from Foundation import NSData, "
        "NSPropertyListSerialization' in " + __name__
    )
    print(
        "WARNING: Failed 'from Foundation import "
        "NSPropertyListMutableContainers' in " + __name__
    )
#pylint: enable=no-name-in-module

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

    def read_bundle_info(self, path):
        """Read Contents/Info.plist inside a bundle."""
        #pylint: disable=no-self-use

        plistpath = os.path.join(path, "Contents", "Info.plist")
        #pylint: disable=line-too-long
        info, _, error = (
            NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(
                NSData.dataWithContentsOfFile_(plistpath),
                NSPropertyListMutableContainers,
                None,
                None))
        #pylint: enable=line-too-long

        if error:
            raise ProcessorError("Can't read %s: %s" % (plistpath, error))

        return info

    def main(self):
        # Mount the image.
        mount_point = self.mount(self.env["dmg_path"])
        # Wrap all other actions in a try/finally so the image is always
        # unmounted.
        try:
            app_path = self.find_app(mount_point)
            info = self.read_bundle_info(app_path)
            self.env["app_name"] = os.path.basename(app_path)
            try:
                self.env["bundleid"] = info["CFBundleIdentifier"]
                self.env["version"] = info["CFBundleShortVersionString"]
                self.output("BundleID: %s" % self.env["bundleid"])
                self.output("Version: %s" % self.env["version"])
            except BaseException as err:
                raise ProcessorError(err)
        finally:
            self.unmount(self.env["dmg_path"])


if __name__ == '__main__':
    PROCESSOR = AppDmgVersioner()
    PROCESSOR.execute_shell()
