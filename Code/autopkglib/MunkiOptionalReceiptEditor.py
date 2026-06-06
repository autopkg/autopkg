#!/usr/local/autopkg/python
#
# Copyright 2014 Jesse Peterson
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
"""See docstring for MunkiOptionalReceiptEditor class"""

import plistlib

from autopkglib import Processor, ProcessorError
from autopkglib.munkirepolibs import fetch_repo_library

__all__ = ["MunkiOptionalReceiptEditor"]


class MunkiOptionalReceiptEditor(Processor):
    """Modifies the receipts key in a Munki pkginfo."""

    description = __doc__
    lifecycle = {"introduced": "2.7"}
    input_variables = {
        "pkginfo_repo_path": {
            "required": True,
            "description": "The repo path where the pkginfo was written.",
        },
        "pkg_ids_set_optional_true": {
            "required": True,
            "description": "Array of package IDs to turn optional for Munki",
        },
        "MUNKI_REPO": {
            "required": True,
            "description": "Path to a mounted Munki repo.",
        },
        "MUNKI_REPO_PLUGIN": {
            "required": False,
            "description": (
                "Munki repo plugin. Defaults to FileRepo. Munki must be installed and available "
                "at MUNKILIB_DIR if a plugin other than FileRepo is specified."
            ),
            "default": "FileRepo",
        },
        "MUNKILIB_DIR": {
            "required": False,
            "description": (
                "Directory path that contains munkilib. Defaults to /usr/local/munki"
            ),
            "default": "/usr/local/munki",
        },
        "force_munki_repo_lib": {
            "required": False,
            "description": (
                "When True, munki code libraries will be utilized when the FileRepo plugin is "
                "used. Munki must be installed and available at MUNKILIB_DIR"
            ),
            "default": False,
        },
        "repo_subdirectory": {
            "required": False,
            "description": (
                "The subdirectory under pkgs and pkgsinfo associated with this pkginfo."
            ),
        },
    }
    output_variables = {
        "munki_info": {
            "description": "The updated pkginfo dictionary.",
        },
    }

    def main(self) -> None:
        if len(self.env["pkginfo_repo_path"]) < 1:
            self.output("No pkginfo_repo_path specified, skipping")
            self.env.setdefault("munki_info", {})
            return

        if "munki_info" in self.env and self.env["munki_info"]:
            pkginfo = self.env["munki_info"]
        else:
            with open(self.env["pkginfo_repo_path"], "rb") as f:
                pkginfo = plistlib.load(f)

        receipts_modified = []
        if "receipts" in pkginfo.keys():
            for i, receipt in enumerate(pkginfo["receipts"]):
                # made optional any pkginfos
                if receipt["packageid"] in self.env["pkg_ids_set_optional_true"]:
                    pkginfo["receipts"][i]["optional"] = True
                    self.output(
                        f"Setting package ID {receipt['packageid']} as optional"
                    )
                    receipts_modified.append(receipt["packageid"])
        else:
            raise ProcessorError("pkginfo does not contain any receipts")

        if len(receipts_modified) > 0:
            library = fetch_repo_library(
                self.env["MUNKI_REPO"],
                self.env["MUNKI_REPO_PLUGIN"],
                self.env["MUNKILIB_DIR"],
                self.env.get("repo_subdirectory"),
                self.env["force_munki_repo_lib"],
            )
            self.output(f"Writing pkginfo to {self.env['pkginfo_repo_path']}")
            library.put_pkginfo_to_repo(pkginfo, self.env["pkginfo_repo_path"])
        else:
            self.output("No receipts modified, nothing to do")

        self.env["munki_info"] = pkginfo


if __name__ == "__main__":
    PROCESSOR = MunkiOptionalReceiptEditor()
    PROCESSOR.execute_shell()
