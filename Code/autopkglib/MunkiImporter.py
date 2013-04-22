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
import subprocess
import plistlib
import shutil

from autopkglib import Processor, ProcessorError


__all__ = ["MunkiImporter"]


class MunkiImporter(Processor):
    """Imports a pkg or dmg to the Munki repo."""
    input_variables = {
        "pkg_path": {
            "required": True,
            "description": "Path to a pkg or dmg to import.",
        },
        "munkiimport_pkgname": {
            "required": False,
            "description": "Corresponds to --pkgname option to munkiimport.",
        },
        "munkiimport_appname": {
            "required": False,
            "description": "Corresponds to --appname option to munkiimport.",
        },
        "repo_subdirectory": {
            "required": False,
            "description": ("The subdirectory under pkgs to which the item "
                "will be copied, and under pkgsinfo where the pkginfo will "
                "be created."),
        },
        "pkginfo": {
            "required": False,
            "description": ("Dictionary of pkginfo keys to copy to "
                "generated pkginfo."),
        },
        "force_munkiimport": {
            "required": False,
            "description": ("If not False or Null, causes the pkg/dmg to be "
                "imported even if there is a matching pkg already in the "
                "repo."),        
        },
    }
    output_variables = {
        "pkginfo_repo_path": {
            "description": ("The repo path where the pkginfo was written. "
                "Empty if item not imported."),
        },
        "pkg_repo_path": {
            "description": ("The repo path where the pkg was written. "
                "Empty if item not imported."),
        },
        "munki_info": {
            "description": 
                "The pkginfo property list. Empty if item not imported.",
        },
        "munki_repo_changed": {
            "description": "True if item was imported."
        },
    }
    description = __doc__
    
    def findMatchingItemInRepo(self, pkginfo):
        """Looks through all catalog for matching installer_item_hash"""
        if not pkginfo.get('installer_item_hash'):
            return None
            
        if self.env.get("force_munkiimport"):
            # we need to import even if there's a match, so skip
            # the check
            return None
            
        repo_path = self.env["MUNKI_REPO"]
        all_items_path = os.path.join(repo_path, 'catalogs', 'all')
        if not os.path.exists(all_items_path):
            raise ProcessorError("Could not find 'all' catalog in Munki repo")
        try:
            catalogitems = plistlib.readPlist(all_items_path)
        except OSErr, err:
            raise ProcessorError(
                "Error reading 'all' catalog from Munki repo: %s" % err)
        
        hash_table = {}
        itemindex = -1
        for item in catalogitems:
            itemindex = itemindex + 1
            # add to hash table
            if 'installer_item_hash' in item:
                if not item['installer_item_hash'] in hash_table:
                    hash_table[item['installer_item_hash']] = []
                hash_table[item['installer_item_hash']].append(itemindex)
                
        matchingindexes = hash_table.get(pkginfo['installer_item_hash'])
        if matchingindexes:
            return catalogitems[matchingindexes[0]]
        else:
            return None
    
    def copyItemToRepo(self, pkginfo):
        """Copies an item to the appropriate place in the repo.
        If itempath is a path within the repo/pkgs directory, copies nothing.
        Renames the item if an item already exists with that name.
        Returns the relative path to the item."""
        
        itempath = self.env["pkg_path"]
        repo_path = self.env["MUNKI_REPO"]
        subdirectory = self.env.get("repo_subdirectory", "")
        item_version = pkginfo.get("version")
        
        if not os.path.exists(repo_path):
            raise ProcessorError("Munki repo not available at %s." % repo_path)

        destination_path = os.path.join(repo_path, "pkgs", subdirectory)
        if not os.path.exists(destination_path):
            try:
                os.makedirs(destination_path)
            except OSError, err:
                raise ProcessorError("Could not create %s: %s" %
                                        (destination_path, err.strerror))

        item_name = os.path.basename(itempath)
        destination_pathname = os.path.join(destination_path, item_name)

        if itempath == destination_pathname:
            # we've been asked to 'import' an item already in the repo.
            # just return the relative path
            return os.path.join(subdirectory, item_name)

        if item_version:
            name, ext = os.path.splitext(item_name)
            if not name.endswith(item_version):
                # add the version number to the end of
                # the item name
                item_name = "%s-%s%s" % (name, item_version, ext)
                destination_pathname = os.path.join(
                    destination_path, item_name)

        index = 0
        name, ext = os.path.splitext(item_name)
        while os.path.exists(destination_pathname):
            # try appending numbers until we have a unique name
            index += 1
            item_name = "%s__%s%s" % (name, index, ext)
            destination_pathname = os.path.join(destination_path, item_name)

        try:
            shutil.copy(itempath, destination_pathname)
        except OSError, err:
            raise ProcessorError(
                "Can't copy %s to %s: %s" 
                % (self.env["pkg_path"], destination_pathname, err.strerror))

        return os.path.join(subdirectory, item_name)

    def copyPkginfoToRepo(self, pkginfo):
        """Saves pkginfo to munki_repo_path/pkgsinfo/subdirectory"""
        # less error checking because we copy the installer_item
        # first and bail if it fails...
        repo_path = self.env["MUNKI_REPO"]
        subdirectory = self.env.get("repo_subdirectory", "")
        destination_path = os.path.join(repo_path, "pkgsinfo", subdirectory)
        if not os.path.exists(destination_path):
            try:
                os.makedirs(destination_path)
            except OSError, err:
                raise ProcessorError("Could not create %s: %s"
                                      % (destination_path, err.strerror))

        pkginfo_name = "%s-%s.plist" % (pkginfo["name"], pkginfo["version"])
        pkginfo_path = os.path.join(destination_path, pkginfo_name)
        index = 0
        while os.path.exists(pkginfo_path):
            index += 1
            pkginfo_name = "%s-%s__%s.plist" % (
                pkginfo["name"], pkginfo["version"], index)
            pkginfo_path = os.path.join(destination_path, pkginfo_name)

        try:
            plistlib.writePlist(pkginfo, pkginfo_path)
        except OSError, err:
            raise ProcessorError("Could not write pkginfo %s: %s"
                                 % (pkginfo_path, err.strerror))
        return pkginfo_path
    
    def main(self):
        
        # Generate arguments for makepkginfo.
        args = ["/usr/local/munki/makepkginfo", self.env["pkg_path"]]
        if self.env.get("munkiimport_pkgname"):
            args.extend(["--pkgname", self.env["munkiimport_pkgname"]])
        if self.env.get("munkiimport_appname"):
            args.extend(["--appname", self.env["munkiimport_appname"]])
        
        # Call makepkginfo.
        try:
            proc = subprocess.Popen(
                args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (out, err_out) = proc.communicate()
        except OSError as err:
            raise ProcessorError(
                "makepkginfo execution failed with error code %d: %s" 
                % (err.errno, err.strerror))
        if proc.returncode != 0:
            raise ProcessorError(
                "creating pkginfo for %s failed: %s" 
                % (self.env["pkg_path"], err_out))
        
        # Get pkginfo from output plist.
        pkginfo = plistlib.readPlistFromString(out)
        
        # check to see if this item is already in the repo
        matchingitem = self.findMatchingItemInRepo(pkginfo)
        if matchingitem:
            self.env["pkginfo_repo_path"] = ""
            # set env["pkg_repo_path"] to the path of the matching item
            self.env["pkg_repo_path"] = os.path.join(
                self.env["MUNKI_REPO"], "pkgs",
                matchingitem['installer_item_location'])
            self.env["munki_info"] = {}
            if not "munki_repo_changed" in self.env:
                self.env["munki_repo_changed"] = False
            
            self.output("Item %s already exists in the munki repo as %s."
                % (os.path.basename(self.env["pkg_path"]),
                   "pkgs/" + matchingitem['installer_item_location']))
                
            return
        
        # copy any keys from pkginfo in self.env
        if "pkginfo" in self.env:
            for key in self.env["pkginfo"]:
                pkginfo[key] = self.env["pkginfo"][key]
                
        # copy pkg/dmg to repo
        relative_path = self.copyItemToRepo(pkginfo)
        # adjust the installer_item_location to match the actual location
        # and name
        pkginfo["installer_item_location"] = relative_path
        
        # set output variables
        self.env["pkginfo_repo_path"] = self.copyPkginfoToRepo(pkginfo)
        self.env["pkg_repo_path"] = os.path.join(
            self.env["MUNKI_REPO"], "pkgs", relative_path)
        self.env["munki_info"] = pkginfo
        self.env["munki_repo_changed"] = True
        
        self.output("Copied pkginfo to %s" % self.env["pkginfo_repo_path"])
        self.output("Copied pkg to %s" % self.env["pkg_repo_path"])

if __name__ == "__main__":
    processor = MunkiImporter()
    processor.execute_shell()