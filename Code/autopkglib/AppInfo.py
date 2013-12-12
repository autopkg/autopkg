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
    description = "Extracts information from a plist file."
    input_variables = {
        "info_path": {
            "required": True,
            "description": "Path to dmg, an app, or any plist. If it is enclosed in a dmg, it will be mounted.",
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

    def find_app(self, path):
        """Find app bundle at path."""
        
        apps = glob.glob(os.path.join(path, "*.app"))
        if len(apps) == 0:
            raise ProcessorError("No app found in dmg")
        return apps[0]
    
    def main(self):
        # Many types of paths are accepted. Figure out which kind we have.
        # Remove any trailing slashes.
        path = os.path.normpath(self.env['info_path'])

        try:
            # Wrap all other actions in a try/finally so if we mount an image,
            # it will always be unmounted.

            # Check if we're trying to read something inside a dmg.
            if '.dmg' in path:
                (dmg_path, dmg, dmg_source_path) = path.partition(".dmg")
                dmg_path += ".dmg"

                mount_point = self.mount(dmg_path)
                path = os.path.join(mount_point, dmg_source_path.lstrip('/'))
            else:
                dmg = False

            if path.endswith('.plist'):
                # Full path to a plist was supplied, move on.
                pass
            # Does the path specify an app?
            elif not '.app' in path:
                path = self.find_app(path)

            # If given path is to an app, assume we want to read the Info.plist.
            if path.endswith('.app'):
                path = os.path.join(path, 'Contents', 'Info.plist')

            #DEBUG
            print path

            try:
                info = FoundationPlist.readPlist(path)
                #self.env["app_name"] = os.path.basename(path)
                self.env["app_name"] = info["CFBundleName"]
                self.env["bundleid"] = info["CFBundleIdentifier"]
                version_key = self.env.get("version_key",
                                           "CFBundleShortVersionString")
                self.env["version"] = info[version_key]
                self.output("AppName:: %s" % self.env["app_name"])
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
