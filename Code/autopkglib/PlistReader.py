#!/usr/local/autopkg/python
#
# Copyright 2013 Shea Craig
# Mostly just reworked code from Per Olofsson/AppDmgVersioner.py and
# Greg Neagle/Versioner.py
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
"""See docstring for PlistReader class"""

import glob
import os.path
import plistlib

from autopkglib import ProcessorError
from autopkglib.DmgMounter import DmgMounter

__all__ = ["PlistReader"]


class PlistReader(DmgMounter):
    """Extracts values from top-level keys in a plist file, and assigns to
    arbitrary output variables. This behavior is different from other
    processors that pre-define all their possible output variables.
    As it is often used for versioning, it defaults to extracting
    'CFBundleShortVersionString' to 'version'. This can be used as a replacement
    for both the AppDmgVersioner and Versioner processors.

    Requires version 0.2.5."""

    description = __doc__
    input_variables = {
        "info_path": {
            "required": True,
            "description": (
                "Path to a plist to be read. If a path to a bundle "
                "(ie. a .app) is given, its Info.plist will be found and used. "
                "If the path is a folder, it will be searched and the first "
                "found bundle will be used. The path can also "
                "contain a dmg/iso file and it will be mounted."
            ),
        },
        "plist_keys": {
            "required": False,
            "default": {"CFBundleShortVersionString": "version"},
            "description": (
                "Dictionary of plist values to query. Key names "
                "should match a top-level key to read. Values "
                "should be the desired output variable name. "
                "Defaults to: ",
                "{'CFBundleShortVersionString': 'version'}",
            ),
        },
    }
    output_variables = {
        "plist_reader_output_variables": {
            "description": (
                "Output variables per 'plist_keys' supplied as "
                "input. Note that this output variable is used as both a "
                "placeholder for documentation and for auditing purposes. "
                "One should use the actual named output variables as given "
                "as values to 'plist_keys' to refer to the output of this "
                "processor."
            )
        }
    }

    def find_bundle(self, path):
        """Returns the first bundle that is found within the top level
        of 'path', or None."""
        files = glob.glob(os.path.join(path, "*"))
        if len(files) == 0:
            raise ProcessorError("No bundle found in dmg")

        # filter out any symlinks that don't have extensions
        # - common case is a symlink to 'Applications', which
        #   we don't want to exhaustively search
        filtered = [
            f
            for f in files
            if not (os.path.islink(f) and not os.path.splitext(os.path.basename(f))[1])
        ]

        for test_bundle in filtered:
            bundle_path = self.get_bundle_info_path(test_bundle)
            if bundle_path:
                return bundle_path
        return None

    def get_bundle_info_path(self, path):
        """Return full path to an Info.plist if 'path' is actually a bundle,
        otherwise None."""
        bundle_info_path = None
        if os.path.isdir(path):
            test_info_path = os.path.join(path, "Contents/Info.plist")
            if os.path.exists(test_info_path):
                try:
                    with open(test_info_path, "rb") as f:
                        plist = plistlib.load(f)
                except Exception:
                    raise ProcessorError(
                        f"File {path} looks like a bundle, but its "
                        "'Contents/Info.plist' file cannot be parsed."
                    )
                if plist:
                    bundle_info_path = test_info_path
        return bundle_info_path

    def main(self) -> None:
        keys = self.env.get("plist_keys")

        # Many types of paths are accepted. Figure out which kind we have.
        path = os.path.normpath(self.env["info_path"])

        try:
            # Wrap all other actions in a try/finally so if we mount an image,
            # it will always be unmounted.

            # Check if we're trying to read something inside a dmg.
            (dmg_path, dmg, dmg_source_path) = self.parsePathForDMG(path)
            if dmg:
                mount_point = self.mount(dmg_path)
                path = os.path.join(mount_point, dmg_source_path.lstrip("/"))

            # Finally check whether this is at least a valid path
            if not os.path.exists(path):
                raise ProcessorError(f"Path '{path}' doesn't exist!")

            # Is the path a bundle?
            info_plist_path = self.get_bundle_info_path(path)
            if info_plist_path:
                path = info_plist_path

            # Does it have a 'plist' extension
            # (naively assuming 'plist' only names, for now)
            elif path.endswith(".plist"):
                # Full path to a plist was supplied, move on.
                pass

            # Might the path contain a bundle at its root?
            else:
                path = self.find_bundle(path)

            # Try to read the plist
            self.output(f"Reading: {path}")
            try:
                with open(path, "rb") as f:
                    info = plistlib.load(f)
            except Exception as err:
                raise ProcessorError(err)

            # Copy each plist_keys' values and assign to new env variables
            self.env["plist_reader_output_variables"] = {}
            for key, val in list(keys.items()):
                try:
                    self.env[val] = info[key]
                    self.output(
                        f"Assigning value of '{self.env[val]}' to output "
                        f"variable '{val}'"
                    )
                    # This one is for documentation/recordkeeping
                    self.env["plist_reader_output_variables"][val] = self.env[val]
                except KeyError:
                    raise ProcessorError(
                        f"Key '{key}' could not be found in the plist {path}!"
                    )

        finally:
            if dmg:
                self.unmount(dmg_path)


if __name__ == "__main__":
    PROCESSOR = PlistReader()
    PROCESSOR.execute_shell()
