#!/Library/AutoPkg/Python3/Python.framework/Versions/Current/bin/python3
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
"""See docstring for MunkiPkginfoMerger class"""

from autopkglib import Processor

__all__ = ["MunkiPkginfoMerger"]


class MunkiPkginfoMerger(Processor):
    """Merges two pkginfo dictionaries."""

    input_variables = {
        "pkginfo": {"required": False, "description": "Dictionary of Munki pkginfo."},
        "additional_pkginfo": {
            "required": True,
            "description": (
                "Dictionary containing additional Munki pkginfo. "
                "This will be added to or replace keys in the pkginfo."
            ),
        },
    }
    output_variables = {"pkginfo": {"description": "Merged pkginfo."}}
    description = __doc__

    def main(self):
        if "pkginfo" not in self.env:
            self.env["pkginfo"] = {}

        for key in list(self.env["additional_pkginfo"].keys()):
            self.env["pkginfo"][key] = self.env["additional_pkginfo"][key]
        self.output("Merged %s into pkginfo" % self.env["additional_pkginfo"])


if __name__ == "__main__":
    PROCESSOR = MunkiPkginfoMerger()
    PROCESSOR.execute_shell()
