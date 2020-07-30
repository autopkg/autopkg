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
from autopkglib.munkirepolibs.MunkiLibAdapter import MunkiLibAdapter

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
            return MunkiLibAdapter(
                munki_repo, munki_repo_plugin, munkilib_dir, repo_subdirectory
            )

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
            matchingitem = None
        else:
            matchingitem = library.find_matching_pkginfo(pkginfo)

        if matchingitem:
            self.env["pkginfo_repo_path"] = ""
            self.env["pkg_repo_path"] = os.path.join(
                self.env["MUNKI_REPO"], "pkgs", matchingitem["installer_item_location"]
            )
            self.env["munki_info"] = {}
            if "munki_repo_changed" not in self.env:
                self.env["munki_repo_changed"] = False

            self.output(
                f"Item {os.path.basename(self.env['pkg_path'])} already exists in the "
                f"munki repo as pkgs/{matchingitem['installer_item_location']}."
            )
            return

        # import pkg
        install_path = library.copy_pkg_to_repo(pkginfo, self.env["pkg_path"])
        pkginfo["installer_item_location"] = install_path.partition("pkgs/")[2]
        self.env["pkg_repo_path"] = install_path

        if self.env.get("uninstaller_pkg_path"):
            uninstall_path = library.copy_pkg_to_repo(
                pkginfo, self.env.get("uninstaller_pkg_path")
            )
            pkginfo["uninstaller_item_location"] = uninstall_path
            pkginfo["uninstallable"] = True

        # import icon
        icon_path = None
        if self.env.get("extract_icon"):
            # munki library is needed to extract and import icons
            if isinstance(library, MunkiLibAdapter):
                icon_library = library
            else:
                icon_library = MunkiLibAdapter(
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

        self.env["icon_repo_path"] = icon_path or ""

        # import pkginfo
        pkginfo_path = library.copy_pkginfo_to_repo(
            pkginfo, self.env.get("MUNKI_PKGINFO_FILE_EXTENSION", "plist")
        )

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
                "pkginfo_path": self.env["pkginfo_repo_path"].partition("pkgsinfo/")[2],
                "pkg_repo_path": self.env["pkg_repo_path"].partition("pkgs/")[2],
                "icon_repo_path": self.env["icon_repo_path"].partition("icons/")[2],
            },
        }

        self.output(f'Copied pkginfo to: {self.env["pkginfo_repo_path"]}')
        self.output(f'           pkg to: {self.env["pkg_repo_path"]}')
        if self.env.get("extract_icon"):
            self.output(f'          icon to: {self.env["icon_repo_path"]}')


if __name__ == "__main__":
    PROCESSOR = MunkiImporter()
    PROCESSOR.execute_shell()
