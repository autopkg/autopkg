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
import plistlib
import subprocess

from Processor import Processor, ProcessorError


__all__ = ["MunkiInstallsItemsCreator"]


class MunkiInstallsItemsCreator(Processor):
    description = "Adds or replaces an installs array in a pkginfo file."
    input_variables = {
        "installs_item_paths": {
            "required": True,
            "description": 
                "Array of paths to create installs items for.",
        },
        "faux_root": {
            "required": False,
            "description": "foo bar baz",
        },
        
    }
    output_variables = {
        "additional_pkginfo": {
            "description": "Pkginfo dictionary containing installs array.",
        },
    }
    
    __doc__ = description
    
    
    def createInstallsItems(self):
        faux_root = ""
        if self.env.get("faux_root"):
            faux_root = self.env["faux_root"].rstrip("/")
        
        args = ["/usr/local/munki/makepkginfo"]
        for item in self.env["installs_item_paths"]:
            args.extend(["-f", faux_root + item])
        
        # Call makepkginfo.
        try:
            p = subprocess.Popen(
                args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (out, err) = p.communicate()
        except OSError as e:
            raise ProcessorError(
                "makepkginfo execution failed with error code %d: %s" 
                % (e.errno, e.strerror))
        if p.returncode != 0:
            raise ProcessorError(
                "creating pkginfo failed: %s" % err)

        # Get pkginfo from output plist.
        pkginfo = plistlib.readPlistFromString(out)
        installs_array = pkginfo.get("installs", [])
        
        if faux_root:
            for item in installs_array:
                if item["path"].startswith(faux_root):
                    item["path"] = item["path"][len(faux_root):]
        if not "additional_pkginfo" in self.env:
            self.env["additional_pkginfo"] = {}
        self.env["additional_pkginfo"]["installs"] = installs_array


    def main(self):
        self.createInstallsItems()


if __name__ == "__main__":
    processor = MunkiInstallsItemsCreator()
    processor.execute_shell()
