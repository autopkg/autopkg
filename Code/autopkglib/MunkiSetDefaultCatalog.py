#!/usr/local/autopkg/python
#
# Copyright 2014 Yoann Gini
# Based on MunkiPkginfoMerger.py, copyright 2013 Greg Neagle
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
"""See docstring for MunkiSetDefaultCatalog class"""

from autopkglib import Processor, log

try:
    from Foundation import CFPreferencesCopyAppValue
except ImportError:
    log(
        "WARNING: Failed 'from Foundation import CFPreferencesCopyAppValue' "
        "in " + __name__
    )

__all__ = ["MunkiSetDefaultCatalog"]


class MunkiSetDefaultCatalog(Processor):
    """Edit current munki pkginfo to set the 'catalog' key to the default
    catalog preference for munkiimport (com.googlecode.munki.munkiimport),
    if one has been set. Typically this would be run as a preprocessor."""

    description = __doc__
    lifecycle = {"introduced": "0.4.2"}
    input_variables = {
        "pkginfo": {"required": False, "description": "Dictionary of Munki pkginfo."}
    }
    output_variables = {"pkginfo": {"description": "Updated pkginfo."}}

    def main(self) -> None:
        if "pkginfo" not in self.env:
            self.env["pkginfo"] = {}
        default_catalog = CFPreferencesCopyAppValue(
            "default_catalog", "com.googlecode.munki.munkiimport"
        )
        if default_catalog:
            self.env["pkginfo"]["catalogs"] = [default_catalog]
            self.output(f"Updated target catalogs into pkginfo with {default_catalog}")
        else:
            self.output("No default catalogs found, nothing changed")


if __name__ == "__main__":
    PROCESSOR = MunkiSetDefaultCatalog()
    PROCESSOR.execute_shell()
