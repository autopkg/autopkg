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

from distutils import version

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
    
    def makeCatalogDB(self):
        """Reads the 'all' catalog and returns a dict we can use like a
         database"""
        
        repo_path = self.env["MUNKI_REPO"]
        all_items_path = os.path.join(repo_path, 'catalogs', 'all')
        if not os.path.exists(all_items_path):
            # might be an error, or might be a brand-new empty repo
            catalogitems = []
        else:
            try:
                catalogitems = plistlib.readPlist(all_items_path)
            except OSError, err:
                raise ProcessorError(
                    "Error reading 'all' catalog from Munki repo: %s" % err)

        pkgid_table = {}
        app_table = {}
        installer_item_table = {}
        hash_table = {}

        itemindex = -1
        for item in catalogitems:
            itemindex = itemindex + 1
            name = item.get('name', 'NO NAME')
            vers = item.get('version', 'NO VERSION')

            if name == 'NO NAME' or vers == 'NO VERSION':
                # skip this item
                continue

            # add to hash table
            if 'installer_item_hash' in item:
                if not item['installer_item_hash'] in hash_table:
                    hash_table[item['installer_item_hash']] = []
                hash_table[item['installer_item_hash']].append(itemindex)

            # add to installer item table
            if 'installer_item_location' in item:
                installer_item_name = os.path.basename(
                    item['installer_item_location'])
                if not installer_item_name in installer_item_table:
                    installer_item_table[installer_item_name] = {}
                if not vers in installer_item_table[installer_item_name]:
                    installer_item_table[installer_item_name][vers] = []
                installer_item_table[
                                installer_item_name][vers].append(itemindex)

            # add to table of receipts
            for receipt in item.get('receipts', []):
                try:
                    if 'packageid' in receipt and 'version' in receipt:
                        if not receipt['packageid'] in pkgid_table:
                            pkgid_table[receipt['packageid']] = {}
                        if not vers in pkgid_table[receipt['packageid']]:
                            pkgid_table[receipt['packageid']][vers] = []
                        pkgid_table[receipt['packageid']][
                                                    vers].append(itemindex)
                except TypeError:
                    # skip this receipt
                    continue
                
            # add to table of installed applications
            for install in item.get('installs', []):
                try:
                    if install.get('type') == 'application':
                        if 'path' in install:
                            if not install['path'] in app_table:
                                app_table[install['path']] = {}
                            if not vers in app_table[install['path']]:
                                app_table[install['path']][vers] = []
                            app_table[install['path']][vers].append(itemindex)
                except TypeError:
                    # skip this item
                    continue

        pkgdb = {}
        pkgdb['hashes'] = hash_table
        pkgdb['receipts'] = pkgid_table
        pkgdb['applications'] = app_table
        pkgdb['installer_items'] = installer_item_table
        pkgdb['items'] = catalogitems

        return pkgdb
    
    def findMatchingItemInRepo(self, pkginfo):
        """Looks through all catalog for items matching the one
        described by pkginfo. Returns a matching item if found."""
        
        def compare_version_keys(value_a, value_b):
            """Internal comparison function for use in sorting"""
            return cmp(version.LooseVersion(value_b),
                       version.LooseVersion(value_a))
        
        if not pkginfo.get('installer_item_hash'):
            return None
            
        if self.env.get("force_munkiimport"):
            # we need to import even if there's a match, so skip
            # the check
            return None
        
        if 'installer_item_hash' in pkginfo:
            pkgdb = self.makeCatalogDB()
            matchingindexes = pkgdb['hashes'].get(
                                        pkginfo['installer_item_hash'])
            if matchingindexes:
                return pkgdb['items'][matchingindexes[0]]
        
        if 'receipts' in pkginfo:
            pkgids = [item['packageid']
                      for item in pkginfo['receipts']
                      if 'packageid' in item]
            if pkgids:
                possiblematches = pkgdb['receipts'].get(pkgids[0])
                if possiblematches:
                    versionlist = possiblematches.keys()
                    versionlist.sort(compare_version_keys)
                    # go through possible matches, newest version first
                    for versionkey in versionlist:
                        testpkgindexes = possiblematches[versionkey]
                        for pkgindex in testpkgindexes:
                            testpkginfo = pkgdb['items'][pkgindex]
                            testpkgids = [item['packageid'] for item in
                                          testpkginfo.get('receipts',[])
                                          if 'packageid' in item]
                            if set(testpkgids) == set(pkgids):
                                return testpkginfo
        
        if 'installs' in pkginfo:
            applist = [item for item in pkginfo['installs']
                       if item['type'] == 'application'
                       and 'path' in item]
            if applist:
                app = applist[0]['path']
                possiblematches = pkgdb['applications'].get(app)
                if possiblematches:
                    versionlist = possiblematches.keys()
                    versionlist.sort(compare_version_keys)
                    indexes = pkgdb['applications'][app][versionlist[0]]
                    return pkgdb['items'][indexes[0]]
                    
        # if we get here, we found no matches
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
        similaritem = self.findMatchingItemInRepo(pkginfo)
        if similaritem:
            if pkginfo["version"] == similaritem["version"]:
                self.env["pkginfo_repo_path"] = ""
                # set env["pkg_repo_path"] to the path of the matching item
                self.env["pkg_repo_path"] = os.path.join(
                    self.env["MUNKI_REPO"], "pkgs",
                    similaritem['installer_item_location'])
                self.env["munki_info"] = {}
                if not "munki_repo_changed" in self.env:
                    self.env["munki_repo_changed"] = False
                
                self.output("Item %s already exists in the munki repo as %s."
                    % (os.path.basename(self.env["pkg_path"]),
                       "pkgs/" + similaritem['installer_item_location']))
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