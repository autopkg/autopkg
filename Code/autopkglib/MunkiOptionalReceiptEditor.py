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
    }
    output_variables = {}

    def main(self) -> None:
        if len(self.env["pkginfo_repo_path"]) < 1:
            self.output("No pkginfo_repo_path specified, skipping")
            return

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
            self.output(f"Writing pkginfo to {self.env['pkginfo_repo_path']}")
            with open(self.env["pkginfo_repo_path"], "wb") as f:
                plistlib.dump(pkginfo, f)
        else:
            self.output("No receipts modified, nothing to do")


if __name__ == "__main__":
    PROCESSOR = MunkiOptionalReceiptEditor()
    PROCESSOR.execute_shell()
