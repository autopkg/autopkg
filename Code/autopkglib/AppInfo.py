#!/usr/bin/env python
#
# Copyright 2013 Shea Craig
# Mostly just reworked code from Per Olofsson/AppDmgVersioner.py and
# Greg Neagle/Versioner.py
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


import os.path
import glob
import FoundationPlist

from DmgMounter import DmgMounter
from autopkglib import Processor, ProcessorError


__all__ = ["AppInfo"]


class AppInfo(DmgMounter):
    description = "Extracts bundle ID and version of app inside dmg."
    input_variables = {
        "app_path": {
            "required": True,
            "description": "Path to a app. If it is enclosed in a dmg, it will be mounted.",
        },
        "plist_version_key": {
            "required": False,
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
    

    def main(self):
        # Check if we're trying to read something inside a dmg.
        (dmg_path, dmg, dmg_source_path) = self.env[
            'app_path'].partition(".dmg/")
        dmg_path += ".dmg"
        # Mount the image.
        # Wrap all other actions in a try/finally so the image is always
        # unmounted.
        try:
            if dmg:
                mount_point = self.mount(dmg_path)
                app_path = os.path.join(mount_point, dmg_source_path)
            else:
                app_path = self.env['app_path']

            if app_path.endswith('.app') or app_path.endswith('.app/'):
                app_path = os.path.join(app_path, 'Contents', 'Info.plist')

            print app_path


            self.env["app_name"] = os.path.basename(app_path)
            try:
                info = FoundationPlist.readPlist(app_path)
                self.env["bundleid"] = info["CFBundleIdentifier"]
                version_key = self.env.get("version_key",
                                           "CFBundleShortVersionString")
                self.env["version"] = info[version_key]
                self.output("BundleID: %s" % self.env["bundleid"])
                self.output("Version: %s" % self.env["version"])
            except FoundationPlist.FoundationPlistException, err:
                raise ProcessorError(err)
        finally:
            if dmg:
                self.unmount(dmg_path)
    

if __name__ == '__main__':
    processor = AppInfo()
    processor.execute_shell()
