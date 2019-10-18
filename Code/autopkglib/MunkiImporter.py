#!/usr/bin/python
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
"""See docstring for MunkiImporter class"""

import os
import plistlib
import shutil
import subprocess

from autopkglib import Processor, ProcessorError

__all__ = ["MunkiImporter"]


class MunkiImporter(Processor):
    """Imports a pkg or dmg to the Munki repo."""

    input_variables = {
        "MUNKI_REPO": {
            "description": "Path to a mounted Munki repo.",
            "required": True,
        },
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
            "description": (
                "The subdirectory under pkgs to which the item "
                "will be copied, and under pkgsinfo where the pkginfo will "
                "be created."
            ),
        },
        "pkginfo": {
            "required": False,
            "description": (
                "Dictionary of pkginfo keys to copy to " "generated pkginfo."
            ),
        },
        "force_munkiimport": {
            "required": False,
            "description": (
                "If not False or Null, causes the pkg/dmg to be "
                "imported even if there is a matching pkg already in the "
                "repo."
            ),
        },
        "additional_makepkginfo_options": {
            "required": False,
            "description": (
                "Array of additional command-line options that will "
                "be inserted when calling 'makepkginfo'."
            ),
        },
        "version_comparison_key": {
            "required": False,
            "description": (
                "String to set 'version_comparison_key' for "
                "any generated installs items."
            ),
        },
        "uninstaller_pkg_path": {
            "required": False,
            "description": (
                "Path to an uninstaller pkg, supported for Adobe "
                "installer_type items."
            ),
        },
        "MUNKI_PKGINFO_FILE_EXTENSION": {
            "description": "Extension for output pkginfo files. Default is 'plist'.",
            "required": False,
        },
        "metadata_additions": {
            "description": (
                "A dictionary that will be merged with the pkginfo _metadata.  "
                "Unique keys will be added, but overlapping keys will replace "
                "existing values."
            ),
            "required": False,
        },
    }
    output_variables = {
        "pkginfo_repo_path": {
            "description": (
                "The repo path where the pkginfo was written. "
                "Empty if item not imported."
            )
        },
        "pkg_repo_path": {
            "description": (
                "The repo path where the pkg was written. "
                "Empty if item not imported."
            )
        },
        "munki_info": {
            "description": "The pkginfo property list. Empty if item not imported."
        },
        "munki_repo_changed": {"description": "True if item was imported."},
        "munki_importer_summary_result": {
            "description": "Description of interesting results."
        },
    }
    description = __doc__

    def make_catalog_db(self):
        """Reads the 'all' catalog and returns a dict we can use like a
         database"""

        repo_path = self.env["MUNKI_REPO"]
        all_items_path = os.path.join(repo_path, "catalogs", "all")
        if not os.path.exists(all_items_path):
            # might be an error, or might be a brand-new empty repo
            catalogitems = []
        else:
            try:
                catalogitems = plistlib.readPlist(all_items_path)
            except OSError as err:
                raise ProcessorError(
                    "Error reading 'all' catalog from Munki repo: %s" % err
                )

        pkgid_table = {}
        app_table = {}
        installer_item_table = {}
        hash_table = {}
        checksum_table = {}
        files_table = {}

        itemindex = -1
        for item in catalogitems:
            itemindex = itemindex + 1
            name = item.get("name", "NO NAME")
            vers = item.get("version", "NO VERSION")

            if name == "NO NAME" or vers == "NO VERSION":
                # skip this item
                continue

            # add to hash table
            if "installer_item_hash" in item:
                if not item["installer_item_hash"] in hash_table:
                    hash_table[item["installer_item_hash"]] = []
                hash_table[item["installer_item_hash"]].append(itemindex)

            # add to installer item table
            if "installer_item_location" in item:
                installer_item_name = os.path.basename(item["installer_item_location"])
                if installer_item_name not in installer_item_table:
                    installer_item_table[installer_item_name] = {}
                if vers not in installer_item_table[installer_item_name]:
                    installer_item_table[installer_item_name][vers] = []
                installer_item_table[installer_item_name][vers].append(itemindex)

            # add to table of receipts
            for receipt in item.get("receipts", []):
                try:
                    if "packageid" in receipt and "version" in receipt:
                        pkgid = receipt["packageid"]
                        pkgvers = receipt["version"]
                        if pkgid not in pkgid_table:
                            pkgid_table[pkgid] = {}
                        if pkgvers not in pkgid_table[pkgid]:
                            pkgid_table[pkgid][pkgvers] = []
                        pkgid_table[pkgid][pkgvers].append(itemindex)
                except TypeError:
                    # skip this receipt
                    continue

            # add to table of installed applications
            for install in item.get("installs", []):
                try:
                    if install.get("type") in ("application", "bundle"):
                        if "path" in install:
                            if "version_comparison_key" in install:
                                app_version = install[install["version_comparison_key"]]
                            else:
                                app_version = install["CFBundleShortVersionString"]
                            if install["path"] not in app_table:
                                app_table[install["path"]] = {}
                            if vers not in app_table[install["path"]]:
                                app_table[install["path"]][app_version] = []
                            app_table[install["path"]][app_version].append(itemindex)
                    if install.get("type") == "file":
                        if "path" in install:
                            if "md5checksum" in install:
                                cksum = install["md5checksum"]

                                if cksum not in checksum_table.keys():
                                    checksum_table[cksum] = []

                                checksum_table[cksum].append(
                                    {"path": install["path"], "index": itemindex}
                                )
                            else:
                                path = install["path"]

                                if path not in files_table.keys():
                                    files_table[path] = []

                                files_table[path].append(
                                    {"path": install["path"], "index": itemindex}
                                )

                except (TypeError, KeyError):
                    # skip this item
                    continue

        pkgdb = {}
        pkgdb["hashes"] = hash_table
        pkgdb["receipts"] = pkgid_table
        pkgdb["applications"] = app_table
        pkgdb["installer_items"] = installer_item_table
        pkgdb["checksums"] = checksum_table
        pkgdb["files"] = files_table
        pkgdb["items"] = catalogitems

        return pkgdb

    def find_matching_item_in_repo(self, pkginfo):
        """Looks through all catalog for items matching the one
        described by pkginfo. Returns a matching item if found."""

        if not pkginfo.get("installer_item_hash"):
            return None

        if self.env.get("force_munkiimport"):
            # we need to import even if there's a match, so skip
            # the check
            return None

        pkgdb = self.make_catalog_db()

        # match hashes for the pkg or dmg
        if "installer_item_hash" in pkginfo:
            pkgdb = self.make_catalog_db()
            matchingindexes = pkgdb["hashes"].get(pkginfo["installer_item_hash"])
            if matchingindexes:
                # we have an item with the exact same checksum hash in the repo
                return pkgdb["items"][matchingindexes[0]]

        # try to match against installed applications
        applist = [
            item
            for item in pkginfo.get("installs", [])
            if item.get("type") in ("application", "bundle") and "path" in item
        ]
        if applist:
            matching_indexes = []
            for app in applist:
                app_path = app["path"]
                if "version_comparison_key" in app:
                    app_version = app[app["version_comparison_key"]]
                else:
                    app_version = app["CFBundleShortVersionString"]
                match = pkgdb["applications"].get(app_path, {}).get(app_version)
                if not match:
                    # no entry for app['path'] and app['version']
                    # no point in continuing
                    return None
                else:
                    if not matching_indexes:
                        # store the array of matching item indexes
                        matching_indexes = set(match)
                    else:
                        # we're only interested in items that match
                        # all applications
                        matching_indexes = matching_indexes.intersection(set(match))

            # did we find any matches?
            if matching_indexes:
                return pkgdb["items"][list(matching_indexes)[0]]

        # fall back to matching against receipts
        matching_indexes = []
        for item in pkginfo.get("receipts", []):
            pkgid = item.get("packageid")
            vers = item.get("version")
            if pkgid and vers:
                match = pkgdb["receipts"].get(pkgid, {}).get(vers)
                if not match:
                    # no entry for pkgid and vers
                    # no point in continuing
                    return None
                else:
                    if not matching_indexes:
                        # store the array of matching item indexes
                        matching_indexes = set(match)
                    else:
                        # we're only interested in items that match
                        # all receipts
                        matching_indexes = matching_indexes.intersection(set(match))

        # did we find any matches?
        if matching_indexes:
            return pkgdb["items"][list(matching_indexes)[0]]

        # try to match against install md5checksums
        filelist = [
            item
            for item in pkginfo.get("installs", [])
            if item["type"] == "file" and "path" in item and "md5checksum" in item
        ]
        if filelist:
            for fileitem in filelist:
                cksum = fileitem["md5checksum"]
                if cksum in pkgdb["checksums"]:
                    cksum_matches = pkgdb["checksums"][cksum]
                    for cksum_match in cksum_matches:
                        if cksum_match["path"] == fileitem["path"]:
                            matching_pkg = pkgdb["items"][cksum_match["index"]]

                            # TODO: maybe match pkg name, too?
                            # if matching_pkg['name'] == pkginfo['name']:

                            return matching_pkg

        # Try to match against a simple list of files and paths
        # where our pkginfo version also matches
        path_only_filelist = [
            item
            for item in pkginfo.get("installs", [])
            if item.get("type") == "file"
            and "path" in item
            and "md5checksum" not in item
        ]
        if path_only_filelist:
            for pathitem in path_only_filelist:
                path = pathitem["path"]
                if path in pkgdb["files"]:
                    path_matches = pkgdb["files"][path]
                    for path_match in path_matches:
                        if path_match["path"] == pathitem["path"]:
                            matching_pkg = pkgdb["items"][path_match["index"]]
                            # make sure we do this only for items that also
                            # match our pkginfo version
                            if matching_pkg["version"] == pkginfo["version"]:
                                return matching_pkg

        # if we get here, we found no matches
        return None

    def copy_item_to_repo(self, pkginfo, uninstaller_pkg=False):
        """Copies an item to the appropriate place in the repo.
        If itempath is a path within the repo/pkgs directory, copies nothing.
        Renames the item if an item already exists with that name.
        Returns the relative path to the item.
        uninstaller_pkg should be True if the item is an uninstaller (Adobe).
        """

        itempath = self.env["pkg_path"]
        if uninstaller_pkg:
            itempath = self.env["uninstaller_pkg_path"]
        repo_path = self.env["MUNKI_REPO"]
        subdirectory = self.env.get("repo_subdirectory", "")
        item_version = pkginfo.get("version")

        if not os.path.exists(repo_path):
            raise ProcessorError("Munki repo not available at %s." % repo_path)

        destination_path = os.path.join(repo_path, "pkgs", subdirectory)
        if not os.path.exists(destination_path):
            try:
                os.makedirs(destination_path)
            except OSError as err:
                raise ProcessorError(
                    "Could not create %s: %s" % (destination_path, err.strerror)
                )

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
                destination_pathname = os.path.join(destination_path, item_name)

        index = 0
        name, ext = os.path.splitext(item_name)
        while os.path.exists(destination_pathname):
            # try appending numbers until we have a unique name
            index += 1
            item_name = "%s__%s%s" % (name, index, ext)
            destination_pathname = os.path.join(destination_path, item_name)

        try:
            shutil.copy(itempath, destination_pathname)
        except OSError as err:
            raise ProcessorError(
                "Can't copy %s to %s: %s"
                % (self.env["pkg_path"], destination_pathname, err.strerror)
            )

        return os.path.join(subdirectory, item_name)

    def copy_pkginfo_to_repo(self, pkginfo):
        """Saves pkginfo to munki_repo_path/pkgsinfo/subdirectory.
        Returns full path to the pkginfo in the repo."""
        # less error checking because we copy the installer_item
        # first and bail if it fails...
        repo_path = self.env["MUNKI_REPO"]
        subdirectory = self.env.get("repo_subdirectory", "")
        destination_path = os.path.join(repo_path, "pkgsinfo", subdirectory)
        if not os.path.exists(destination_path):
            try:
                os.makedirs(destination_path)
            except OSError as err:
                raise ProcessorError(
                    "Could not create %s: %s" % (destination_path, err.strerror)
                )

        extension = self.env.get("MUNKI_PKGINFO_FILE_EXTENSION", "plist")
        if len(extension) > 0:
            extension = "." + extension.strip(".")
        pkginfo_name = "%s-%s%s" % (
            pkginfo["name"],
            pkginfo["version"].strip(),
            extension,
        )
        pkginfo_path = os.path.join(destination_path, pkginfo_name)
        index = 0
        while os.path.exists(pkginfo_path):
            index += 1
            pkginfo_name = "%s-%s__%s%s" % (
                pkginfo["name"],
                pkginfo["version"],
                index,
                extension,
            )
            pkginfo_path = os.path.join(destination_path, pkginfo_name)

        try:
            plistlib.writePlist(pkginfo, pkginfo_path)
        except OSError as err:
            raise ProcessorError(
                "Could not write pkginfo %s: %s" % (pkginfo_path, err.strerror)
            )
        return pkginfo_path

    def main(self):
        # clear any pre-exising summary result
        if "munki_importer_summary_result" in self.env:
            del self.env["munki_importer_summary_result"]
        # Generate arguments for makepkginfo.
        args = ["/usr/local/munki/makepkginfo", self.env["pkg_path"]]
        if self.env.get("munkiimport_pkgname"):
            args.extend(["--pkgname", self.env["munkiimport_pkgname"]])
        if self.env.get("munkiimport_appname"):
            args.extend(["--appname", self.env["munkiimport_appname"]])
        # uninstaller pkg will be copied later, this is just to suppress
        # makepkginfo stderr warning output
        if self.env.get("uninstaller_pkg_path"):
            args.extend(["--uninstallpkg", self.env["uninstaller_pkg_path"]])
        if self.env.get("additional_makepkginfo_options"):
            args.extend(self.env["additional_makepkginfo_options"])

        # Call makepkginfo.
        try:
            proc = subprocess.Popen(
                args, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            (out, err_out) = proc.communicate()
        except OSError as err:
            raise ProcessorError(
                "makepkginfo execution failed with error code %d: %s"
                % (err.errno, err.strerror)
            )
        if err_out:
            for err_line in err_out.splitlines():
                self.output(err_line)
        if proc.returncode != 0:
            raise ProcessorError(
                "creating pkginfo for %s failed: %s" % (self.env["pkg_path"], err_out)
            )

        # Get pkginfo from output plist.
        pkginfo = plistlib.readPlistFromString(out)

        # copy any keys from pkginfo in self.env
        if "pkginfo" in self.env:
            for key in self.env["pkginfo"]:
                pkginfo[key] = self.env["pkginfo"][key]

        # copy any keys from metadata_additions
        if "metadata_additions" in self.env:
            pkginfo["_metadata"].update(self.env["metadata_additions"])

        # set an alternate version_comparison_key
        # if pkginfo has an installs item
        if "installs" in pkginfo and self.env.get("version_comparison_key"):
            for item in pkginfo["installs"]:
                if not self.env["version_comparison_key"] in item:
                    raise ProcessorError(
                        (
                            "version_comparison_key '%s' could not be found in "
                            "the installs item for path '%s'"
                        )
                        % (self.env["version_comparison_key"], item["path"])
                    )
                item["version_comparison_key"] = self.env["version_comparison_key"]

        # check to see if this item is already in the repo
        matchingitem = self.find_matching_item_in_repo(pkginfo)
        if matchingitem:
            self.env["pkginfo_repo_path"] = ""
            # set env["pkg_repo_path"] to the path of the matching item
            self.env["pkg_repo_path"] = os.path.join(
                self.env["MUNKI_REPO"], "pkgs", matchingitem["installer_item_location"]
            )
            self.env["munki_info"] = {}
            if "munki_repo_changed" not in self.env:
                self.env["munki_repo_changed"] = False

            self.output(
                "Item %s already exists in the munki repo as %s."
                % (
                    os.path.basename(self.env["pkg_path"]),
                    "pkgs/" + matchingitem["installer_item_location"],
                )
            )
            return

        # copy pkg/dmg to repo
        relative_path = self.copy_item_to_repo(pkginfo)
        # adjust the installer_item_location to match the actual location
        # and name
        pkginfo["installer_item_location"] = relative_path

        if self.env.get("uninstaller_pkg_path"):
            relative_uninstall_path = self.copy_item_to_repo(
                pkginfo, uninstaller_pkg=True
            )
            pkginfo["uninstaller_item_location"] = relative_uninstall_path
            pkginfo["uninstallable"] = True

        # set output variables
        self.env["pkginfo_repo_path"] = self.copy_pkginfo_to_repo(pkginfo)
        self.env["pkg_repo_path"] = os.path.join(
            self.env["MUNKI_REPO"], "pkgs", relative_path
        )
        # update env["pkg_path"] to match env["pkg_repo_path"]
        # this allows subsequent recipe steps to reuse the uploaded
        # pkg/dmg instead of re-uploading
        # This won't affect most recipes, since most have a single
        # MunkiImporter step (and it's usually the last step)
        self.env["pkg_path"] = self.env["pkg_repo_path"]
        self.env["munki_info"] = pkginfo
        self.env["munki_repo_changed"] = True
        self.env["munki_importer_summary_result"] = {
            "summary_text": "The following new items were imported into Munki:",
            "report_fields": [
                "name",
                "version",
                "catalogs",
                "pkginfo_path",
                "pkg_repo_path",
            ],
            "data": {
                "name": pkginfo["name"],
                "version": pkginfo["version"],
                "catalogs": ",".join(pkginfo["catalogs"]),
                "pkginfo_path": self.env["pkginfo_repo_path"].partition("pkgsinfo/")[2],
                "pkg_repo_path": self.env["pkg_repo_path"].partition("pkgs/")[2],
            },
        }

        self.output("Copied pkginfo to %s" % self.env["pkginfo_repo_path"])
        self.output("Copied pkg to %s" % self.env["pkg_repo_path"])


if __name__ == "__main__":
    PROCESSOR = MunkiImporter()
    PROCESSOR.execute_shell()
