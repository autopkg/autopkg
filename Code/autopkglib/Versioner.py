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
"""See docstring for Versioner class"""


import glob
import os.path

from autopkglib import ProcessorError
from autopkglib.DmgMounter import DmgMounter
import FoundationPlist


__all__ = ["Versioner"]
BUNDLE_TYPES = (".app", ".plugin", ".qlgenerator")
BUNDLE_SUFFIX = "Contents/Info.plist"


class Versioner(DmgMounter):
    """Returns version information from a plist"""
    description = __doc__

    input_variables = {
        "input_plist_path": {
            "required": True,
            "description":
                "File path to a plist or a bundle. If the path is relative to "
                "a disk image, that disk image is mounted before parsing the "
                "plist.  If no bundle is specified, Versioner will find the "
                "first bundle at the path, prioritizing apps.",
        },
        "plist_version_key": {
            "required": False,
            "default": "CFBundleShortVersionString",
            "description":
                "Which plist key to use; defaults to "
                "CFBundleShortVersionString",
        },
    }
    output_variables = {
        "app_name": {
            "description": "Name of the app."
        },
        "bundleid": {
            "description": "Bundle identifier of the app.",
        },
        "version": {
            "description": "Version of the item.",
        },
    }

    def main(self):
        """Return an app name, bundleid, and version for file."""
        input_plist_path = self.env["input_plist_path"]

        if self.is_image(input_plist_path):
            results = self.get_plist_from_dmg(input_plist_path)
        else:
            results = self.get_plist_from_path(input_plist_path)

        self.set_output_variables(*results)

    def is_image(self, path):
        """Return bool whether path includes an image component."""
        return any(ext in path for ext in self.DMG_EXTENSIONS)

    def get_plist_from_dmg(self, input_plist_path):
        """Get a plist and its path if found in a dmg

        Searches for bundles if none are included.
        """
        (dmg_path, dmg, _) = (
            self.parsePathForDMG(input_plist_path))

        if dmg or dmg_path.endswith(tuple(self.DMG_EXTENSIONS)):
            try:
                mount_point = self.mount(dmg_path)
                plist, plist_path = self.get_plist_from_path(mount_point)
            finally:
                self.unmount(dmg_path)
        return (plist, plist_path)

    def get_plist_from_path(self, input_plist_path):
        """Get a plist and its path if found in a bundle."""
        plist_path = self.parse_input_path(input_plist_path)
        return (self.get_plist(plist_path), plist_path)

    def parse_input_path(self, plist_path):
        """Ensure a path includes a valid bundle Info.plist.

        If a path does not include a bundle, look for the first bundle
        at path.

        If a path does not include the suffix Contents/Info.plist, add
        it.
        """
        if not plist_path.endswith(BUNDLE_SUFFIX):
            if not plist_path.endswith(BUNDLE_TYPES):
                plist_path = self.find_bundle(plist_path)

            plist_path = os.path.join(plist_path, BUNDLE_SUFFIX)
        return plist_path

    def find_bundle(self, path):
        """Find first bundle at path.

        Priority is:
            .app
            .plugin
            .qlgenerator

        Returns:
            String path to found bundle, or None.
        """
        #pylint: disable=no-self-use
        for bundle_type in BUNDLE_TYPES:
            bundle = glob.glob(os.path.join(path, "*%s" % bundle_type))
            if len(bundle):
                result = bundle[0]
                self.output("Found bundle %s" % result)
                return result

    def get_plist(self, plist_path):
        """Return a plist object from file at plist_path."""
        #pylint: disable=no-self-use
        if os.path.exists(plist_path):
            try:
                plist = FoundationPlist.readPlist(plist_path)
            except FoundationPlist.FoundationPlistException as err:
                raise ProcessorError(err)
        else:
            raise ProcessorError(
                "File '%s' does not exist or could not be read." %
                plist_path)
        return plist

    def set_output_variables(self, plist, plist_path):
        """Set output variables based on plist."""
        self.env["app_name"] = self.get_app_name(plist_path)
        self.output("Found app_name %s in file %s" % (
            self.env["app_name"], plist_path))

        self.env["bundleid"] = plist.get(
            "CFBundleIdentifier", "UNKNOWN_BUNDLE_ID")
        self.output("Found bundleid %s in file %s" % (
            self.env["bundleid"], plist_path))

        version_key = self.env.get("plist_version_key")
        self.env["version"] = plist.get(version_key, "UNKNOWN_VERSION")
        self.output("Found version %s in file %s"
                    % (self.env["version"], plist_path))

    def get_app_name(self, path):
        """Return the app filename component of a path."""
        #pylint: disable=no-self-use
        return os.path.basename(path.split("/" + BUNDLE_SUFFIX)[0])


if __name__ == "__main__":
    PROCESSOR = Versioner()
    PROCESSOR.execute_shell()

