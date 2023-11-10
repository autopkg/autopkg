#!/usr/local/autopkg/python
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
import subprocess

from autopkglib import Processor, ProcessorError
from autopkglib.munkirepolibs.AutoPkgLib import AutoPkgLib
from autopkglib.munkirepolibs.MunkiLib import MunkiLib

__all__ = ["MunkiImporter"]


class MunkiImporter(Processor):
    """Imports a pkg or dmg to the Munki repo."""

    input_variables = {
        "MUNKI_REPO": {
            "description": "Path to a mounted Munki repo.",
            "required": True,
        },
        "MUNKI_REPO_PLUGIN": {
            "description": (
                "Munki repo plugin. Defaults to FileRepo. Munki must be installed and available "
                " at MUNKILIB_DIR if a plugin other than FileRepo is specified."
            ),
            "required": False,
            "default": "FileRepo",
        },
        "MUNKILIB_DIR": {
            "description": (
                "Directory path that contains munkilib. Defaults to /usr/local/munki"
            ),
            "required": False,
            "default": "/usr/local/munki",
        },
        "force_munki_repo_lib": {
            "description": (
                "When True, munki code libraries will be utilized when the FileRepo plugin is "
                "used. Munki must be installed and available at MUNKILIB_DIR"
            ),
            "required": False,
            "default": False,
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
            "description": ("Dictionary of pkginfo keys to copy to generated pkginfo."),
        },
        "extract_icon": {
            "required": False,
            "description": (
                "If not empty, attempt to extract and import an icon from the installer item. "
                "Munki must be installed and available at MUNKILIB_DIR."
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

    def _fetch_repo_library(
        self,
        munki_repo,
        munki_repo_plugin,
        munkilib_dir,
        repo_subdirectory,
        force_munki_lib,
    ):
        if munki_repo_plugin == "FileRepo" and not force_munki_lib:
            return AutoPkgLib(munki_repo, repo_subdirectory)
        else:
            return MunkiLib(
                munki_repo, munki_repo_plugin, munkilib_dir, repo_subdirectory
            )

    def _find_matching_pkginfo(self, repo_library, pkginfo):
        """Looks through all catalog for items matching the one
        described by pkginfo. Returns a list of matching items if found."""
        if not pkginfo.get("installer_item_hash"):
            return None

        pkgdb = repo_library.make_catalog_db()
        # match hashes for the pkg or dmg
        if "installer_item_hash" in pkginfo:
            matchingindexes = pkgdb["hashes"].get(pkginfo["installer_item_hash"])
            if matchingindexes:
                # we have an item with the exact same checksum hash in the repo
                return [
                    pkgdb["items"][matchingindex]
                    for matchingindex in list(matchingindexes)
                ]

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
                return [
                    pkgdb["items"][matching_index]
                    for matching_index in list(matching_indexes)
                ]

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
            return [
                pkgdb["items"][matching_index]
                for matching_index in list(matching_indexes)
            ]

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

                            return [matching_pkg]

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
                                return [matching_pkg]

        # if we get here, we found no matches
        return None

    def main(self):
        library = self._fetch_repo_library(
            self.env["MUNKI_REPO"],
            self.env["MUNKI_REPO_PLUGIN"],
            self.env["MUNKILIB_DIR"],
            self.env.get("repo_subdirectory"),
            self.env["force_munki_repo_lib"],
        )

        self.output(f"Using repo lib: {library.__class__.__name__}")
        self.output(f'        plugin: {self.env["MUNKI_REPO_PLUGIN"]}')
        self.output(f'          repo: {self.env["MUNKI_REPO"]}')

        # clear any pre-existing summary result
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
                args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False
            )
            (out, err_out) = proc.communicate()
        except OSError as err:
            raise ProcessorError(
                f"makepkginfo execution failed with error code {err.errno}: "
                f"{err.strerror}"
            )
        if err_out:
            for err_line in err_out.decode().splitlines():
                self.output(err_line)
        if proc.returncode != 0:
            raise ProcessorError(
                f"creating pkginfo for {self.env['pkg_path']} failed: "
                f"{err_out.decode()}"
            )

        # Get pkginfo from output plist.
        pkginfo = plistlib.loads(out)

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
                            "version_comparison_key "
                            f"'{self.env['version_comparison_key']}' could not be "
                            f"found in the installs item for path '{item['path']}'"
                        )
                    )
                item["version_comparison_key"] = self.env["version_comparison_key"]

        # check to see if this item is already in the repo
        if self.env.get("force_munkiimport"):
            matchingitems = None
        else:
            matchingitems = self._find_matching_pkginfo(library, pkginfo)

        archs = []
        if matchingitems:
            archs = [
                matchingitem.get("supported_architectures")
                for matchingitem in matchingitems
            ]

        if matchingitems and (pkginfo.get("supported_architectures") in archs):
            if archs and None not in archs:
                installer_item_location = [
                    matchingitem.get("installer_item_location")
                    for matchingitem in list(matchingitems)
                    if pkginfo.get("supported_architectures")
                    == matchingitem.get("supported_architectures")
                ][0]
            else:
                installer_item_location = matchingitems[0]["installer_item_location"]
            self.env["pkginfo_repo_path"] = ""
            self.env["pkg_repo_path"] = os.path.join(
                self.env["MUNKI_REPO"], "pkgs", installer_item_location
            )
            self.env["munki_info"] = {}
            self.env["munki_repo_changed"] = False

            self.output(
                f"Item {os.path.basename(self.env['pkg_path'])} already exists in the "
                f"munki repo as pkgs/{installer_item_location}."
            )
            return

        # import pkg
        install_path = library.copy_pkg_to_repo(pkginfo, self.env["pkg_path"])
        install_prefix = os.path.join(library.munki_repo, "pkgs")
        pkginfo["installer_item_location"] = os.path.relpath(
            install_path, install_prefix
        )
        self.env["pkg_repo_path"] = install_path

        if self.env.get("uninstaller_pkg_path"):
            uninstall_path = library.copy_pkg_to_repo(
                pkginfo, self.env.get("uninstaller_pkg_path")
            )
            pkginfo["uninstaller_item_location"] = uninstall_path.partition("pkgs/")[2]
            pkginfo["uninstallable"] = True

        # import icon
        icon_path = None
        if self.env.get("extract_icon"):
            # munki library is needed to extract and import icons
            if isinstance(library, MunkiLib):
                icon_library = library
            else:
                icon_library = MunkiLib(
                    self.env["MUNKI_REPO"],
                    self.env["MUNKI_REPO_PLUGIN"],
                    self.env["MUNKILIB_DIR"],
                    self.env.get("repo_subdirectory"),
                )

            icon_path = icon_library.find_matching_icon(pkginfo)

            if not icon_path:
                icon_path = icon_library.extract_and_copy_icon_to_repo(
                    self.env["pkg_path"], pkginfo, import_multiple=False
                )

        if icon_path:
            self.env["icon_repo_path"] = icon_path
            icon_prefix = os.path.join(library.munki_repo, "icons")
            rel_icon_path = os.path.relpath(icon_path, icon_prefix)
        else:
            self.env["icon_repo_path"] = rel_icon_path = ""

        # import pkginfo
        pkginfo_path = library.copy_pkginfo_to_repo(
            pkginfo, self.env.get("MUNKI_PKGINFO_FILE_EXTENSION", "plist")
        )
        pkginfo_prefix = os.path.join(library.munki_repo, "pkgsinfo")
        pkg_prefix = os.path.join(library.munki_repo, "pkgs")

        self.env["pkginfo_repo_path"] = pkginfo_path

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
                "icon_repo_path",
            ],
            "data": {
                "name": pkginfo["name"],
                "version": pkginfo["version"],
                "catalogs": ",".join(pkginfo["catalogs"]),
                "pkginfo_path": os.path.relpath(
                    self.env["pkginfo_repo_path"], pkginfo_prefix
                ),
                "pkg_repo_path": os.path.relpath(self.env["pkg_repo_path"], pkg_prefix),
                "icon_repo_path": rel_icon_path,  # can be path or ""
            },
        }

        self.output(f'Copied pkginfo to: {self.env["pkginfo_repo_path"]}')
        self.output(f'           pkg to: {self.env["pkg_repo_path"]}')
        if self.env.get("extract_icon"):
            self.output(f'          icon to: {self.env["icon_repo_path"]}')


if __name__ == "__main__":
    PROCESSOR = MunkiImporter()
    PROCESSOR.execute_shell()
