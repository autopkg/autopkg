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


import FoundationPlist
import subprocess

from autopkglib import Processor, ProcessorError


__all__ = ["MunkiInstallsItemsCreator"]


class MunkiInstallsItemsCreator(Processor):
    """Generates an installs array for a pkginfo file."""
    input_variables = {
        "installs_item_paths": {
            "required": True,
            "description": 
                "Array of paths to create installs items for.",
        },
        "faux_root": {
            "required": False,
            "description": "The root of an expanded package or filesystem.",
        },
        
    }
    output_variables = {
        "additional_pkginfo": {
            "description": "Pkginfo dictionary containing installs array.",
        },
    }
    description = __doc__
    
    def createInstallsItems(self):
        """Calls makepkginfo to create an installs array."""
        faux_root = ""
        if self.env.get("faux_root"):
            faux_root = self.env["faux_root"].rstrip("/")
        
        args = ["/usr/local/munki/makepkginfo"]
        for item in self.env["installs_item_paths"]:
            args.extend(["-f", faux_root + item])
        
        # Call makepkginfo.
        try:
            proc = subprocess.Popen(
                args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (out, err) = proc.communicate()
        except OSError as err:
            raise ProcessorError(
                "makepkginfo execution failed with error code %d: %s" 
                % (err.errno, err.strerror))
        if proc.returncode != 0:
            raise ProcessorError(
                "creating pkginfo failed: %s" % err)

        # Get pkginfo from output plist.
        pkginfo = FoundationPlist.readPlistFromString(out)
        installs_array = pkginfo.get("installs", [])
        
        if faux_root:
            for item in installs_array:
                if item["path"].startswith(faux_root):
                    item["path"] = item["path"][len(faux_root):]
                self.output("Created installs item for %s" % item["path"])
        if not "additional_pkginfo" in self.env:
            self.env["additional_pkginfo"] = {}
        self.env["additional_pkginfo"]["installs"] = installs_array


    def main(self):
        self.createInstallsItems()


if __name__ == "__main__":
    processor = MunkiInstallsItemsCreator()
    processor.execute_shell()
