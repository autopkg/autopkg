#!/Library/AutoPkg/Python3/Python.framework/Versions/Current/bin/python3
#
# Copyright 2010 Per Olofsson
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
"""See docstring for PkgInfoCreator class"""

import math
import os
import plistlib
from xml.etree import ElementTree

from autopkglib import Processor, ProcessorError

__all__ = ["PkgInfoCreator"]


class PkgInfoCreator(Processor):
    """Creates an PackageInfo file for a package."""

    description = __doc__
    input_variables = {
        "template_path": {"required": True, "description": "An Info.plist template."},
        "version": {"required": True, "description": "Version of the package."},
        "pkgroot": {"required": True, "description": "Virtual root of the package."},
        "infofile": {
            "required": True,
            "description": "Path to the info file to create.",
        },
        "pkgtype": {"required": True, "description": "'flat' or 'bundle'."},
    }
    output_variables = {}

    def find_template(self):
        """Searches for the template, looking in the recipe directory
        and parent recipe directories if needed."""
        template_path = self.env["template_path"]
        if os.path.exists(template_path):
            return template_path
        elif not template_path.startswith("/"):
            recipe_dir = self.env.get("RECIPE_DIR")
            search_dirs = [recipe_dir]
            if self.env.get("PARENT_RECIPES"):
                # also look in the directories containing the parent recipes
                parent_recipe_dirs = list(
                    {os.path.dirname(item) for item in self.env["PARENT_RECIPES"]}
                )
                search_dirs.extend(parent_recipe_dirs)
            for directory in search_dirs:
                test_item = os.path.join(directory, template_path)
                if os.path.exists(test_item):
                    return test_item
        raise ProcessorError(f"Can't find {template_path}")

    def main(self):
        if self.env["pkgtype"] not in ("bundle", "flat"):
            raise ProcessorError(f"Unknown pkgtype {self.env['pkgtype']}")
        template = self.load_template(self.find_template(), self.env["pkgtype"])
        if self.env["pkgtype"] == "bundle":
            raise ProcessorError("Bundle package creation no longer supported!")
        else:
            self.create_flat_info(template)

    def convert_bundle_info_to_flat(self, info):
        """Converts pkg info from bundle format to flat format"""
        # Since we now only support flat packages, we might be able to
        # get rid of this in the near future, but all existing recipes
        # would need to convert to only flat-style Resources/data
        conversion_map = {
            "None": "none",
            "RecommendRestart": "restart",
            "RequireLogout": "logout",
            "RequireRestart": "restart",
            "RequireShutdown": "shutdown",
        }

        pkg_info = ElementTree.Element("pkg-info")
        pkg_info.set("format-version", "2")
        for bundle, flat in (
            ("IFPkgFlagDefaultLocation", "install-location"),
            ("CFBundleShortVersionString", "version"),
            ("CFBundleIdentifier", "identifier"),
        ):
            if bundle in info:
                pkg_info.set(flat, info[bundle])
        if "IFPkgFlagAuthorizationAction" in info:
            if info["IFPkgFlagAuthorizationAction"] == "RootAuthorization":
                pkg_info.set("auth", "root")
            else:
                pkg_info.set("auth", "none")
        if "IFPkgFlagRestartAction" in info:
            pkg_info.set(
                "postinstall-action", conversion_map[info["IFPkgFlagRestartAction"]]
            )

        payload = ElementTree.SubElement(pkg_info, "payload")
        if "IFPkgFlagInstalledSize" in info:
            payload.set("installKBytes", str(info["IFPkgFlagInstalledSize"]))

        return ElementTree.ElementTree(pkg_info)

    def convert_flat_info_to_bundle(self, info):
        """Converts pkg info from flat format to bundle format"""
        # since we now only support flat packages, just raise an exception
        raise ProcessorError("Bundle package creation no longer supported!")

    def load_template(self, template_path, template_type):
        """Load a package info template in Info.plist or PackageInfo format."""

        if template_path.endswith(".plist"):
            # Try to load Info.plist in bundle format.
            try:
                with open(self.env["template_path"], "rb") as f:
                    info = plistlib.load(f)
            except Exception:
                raise ProcessorError(
                    f"Malformed Info.plist template {self.env['template_path']}"
                )
            if template_type == "bundle":
                return info
            else:
                return self.convert_bundle_info_to_flat(info)
        else:
            # Try to load PackageInfo in flat format.
            try:
                info = ElementTree.parse(template_path)
            except Exception:
                raise ProcessorError(
                    f"Malformed PackageInfo template {self.env['template_path']}"
                )
            if template_type == "flat":
                return info
            else:
                return self.convert_flat_info_to_bundle(info)

    def get_pkgroot_size(self, pkgroot):
        """Return the size of pkgroot (in kilobytes) and the number of files."""

        size = 0
        nfiles = 0
        for (dirpath, _, filenames) in os.walk(pkgroot):
            # Count the current directory and the number of files in it.
            nfiles += 1 + len(filenames)
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                # Add up file size rounded up to the nearest 4 kB, which
                # appears to match what du -sk returns, and what PackageMaker
                # uses.
                size += int(math.ceil(float(os.lstat(path).st_size) / 4096.0))

        return (size, nfiles)

    def create_flat_info(self, template):
        """Create PackageInfo file for flat package"""
        info = template

        pkg_info = info.getroot()
        if pkg_info.tag != "pkg-info":
            raise ProcessorError("PackageInfo root should be pkg-info")

        pkg_info.set("version", self.env["version"])

        payload = pkg_info.find("payload")
        if payload is None:
            payload = ElementTree.SubElement(pkg_info, "payload")
        size, nfiles = self.get_pkgroot_size(self.env["pkgroot"])
        payload.set("installKBytes", str(size))
        payload.set("numberOfFiles", str(nfiles))

        info.write(self.env["infofile"])

    def create_bundle_info(self, template):
        """Create Info.plist data for bundle-style pkg"""
        # We don't support the creation of bundle-style pkgs
        # any longer, so raise an exception
        raise ProcessorError("Bundle package creation no longer supported!")


if __name__ == "__main__":
    PROCESSOR = PkgInfoCreator()
    PROCESSOR.execute_shell()
