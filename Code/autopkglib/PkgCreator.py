#!/usr/local/autopkg/python
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
"""See docstring for PkgCreator class"""

import os.path
import plistlib
import socket
import subprocess
from xml.etree import ElementTree as ET

from autopkglib import Processor, ProcessorError

AUTO_PKG_SOCKET = "/var/run/autopkgserver"

__all__ = ["PkgCreator"]


class PkgCreator(Processor):
    """Calls autopkgserver to create a package."""

    description = __doc__
    lifecycle = {"introduced": "0.1.0"}
    input_variables = {
        "pkg_request": {
            "required": True,
            "description": (
                "A package request dictionary. See "
                "Code/autopkgserver/autopkgserver for more details."
            ),
        },
        "force_pkg_build": {
            "required": False,
            "description": (
                "When set, this forces building a new package even if "
                "a package already exists in the output directory with "
                "the same identifier and version number. Defaults to False"
            ),
            "default": False,
        },
    }
    output_variables = {
        "pkg_path": {"description": "The created package."},
        "new_package_request": {
            "description": (
                "True if a new package was actually requested to be built. "
                "False if a package with the same filename, identifier and "
                "version already exists and thus no package was built (see "
                "'force_pkg_build' input variable."
            )
        },
        "pkg_creator_summary_result": {
            "description": "Description of interesting results."
        },
    }

    def find_path_for_relpath(self, relpath):
        """Searches for the relative path.
        Search order is:
            RECIPE_CACHE_DIR
            RECIPE_DIR
            PARENT_RECIPE directories"""
        cache_dir = self.env.get("RECIPE_CACHE_DIR")
        recipe_dir = self.env.get("RECIPE_DIR")
        search_dirs = [cache_dir, recipe_dir]
        if self.env.get("PARENT_RECIPES"):
            # also look in the directories containing the parent recipes
            parent_recipe_dirs = list(
                {os.path.dirname(item) for item in self.env["PARENT_RECIPES"]}
            )
            search_dirs.extend(parent_recipe_dirs)
        for directory in search_dirs:
            test_item = os.path.join(directory, relpath)
            if os.path.exists(test_item):
                return os.path.normpath(test_item)

        raise ProcessorError(f"Can't find {relpath}")

    def xar_expand(self, source_path) -> None:
        """Uses xar to expand an archive"""
        try:
            xarcmd = [
                "/usr/bin/xar",
                "-x",
                "-C",
                self.env.get("RECIPE_CACHE_DIR"),
                "-f",
                source_path,
                "PackageInfo",
            ]
            proc = subprocess.Popen(
                xarcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            (_, stderr) = proc.communicate()
        except OSError as err:
            raise ProcessorError(
                f"xar execution failed with error code {err.errno}: {err.strerror}"
            )
        if proc.returncode != 0:
            raise ProcessorError(
                f"extraction of {source_path} with xar failed: {stderr}"
            )

    def pkg_already_exists(self, pkg_path, identifier, version) -> bool:
        """Check for an existing flat package in the output dir and compare its
        identifier and version to the one we're going to build.
        Returns a boolean."""
        if os.path.exists(pkg_path) and not self.env.get("force_pkg_build"):
            self.output(f"Package already exists at path {pkg_path}.")
            try:
                self.xar_expand(pkg_path)
            except ProcessorError as err:
                self.output(err)
                # just remove the pkg and return False
                self.output(f"Removing {pkg_path}")
                try:
                    os.unlink(pkg_path)
                except OSError as err:
                    raise ProcessorError(f"Could not remove {pkg_path}: {err}")
                return False
            packageinfo_file = os.path.join(self.env["RECIPE_CACHE_DIR"], "PackageInfo")
            if not os.path.exists(packageinfo_file):
                self.output(
                    "Failed to parse existing package, as no PackageInfo "
                    "file could be found in the extracted archive."
                )
                # just remove the pkg and return False
                self.output(f"Removing {pkg_path}")
                try:
                    os.unlink(pkg_path)
                except OSError as err:
                    raise ProcessorError(f"Could not remove {pkg_path}: {err}")
                return False
            # parse the PackageInfo file for version and identifier
            tree = ET.parse(packageinfo_file)
            root = tree.getroot()
            local_version = root.attrib["version"]
            local_id = root.attrib["identifier"]
            try:
                # clean up
                os.unlink(packageinfo_file)
            except OSError:
                pass
            if local_version == version and local_id == identifier:
                return True
        return False

    def package(self) -> None:
        """Build a packaging request, send it to the autopkgserver and get the
        constructed package."""

        # clear any pre-existing summary result
        if "pkg_creator_summary_result" in self.env:
            del self.env["pkg_creator_summary_result"]

        request = self.env["pkg_request"]
        if "pkgdir" not in request:
            request["pkgdir"] = self.env["RECIPE_CACHE_DIR"]

        # Set variables, and check that all keys are in request.
        for key in (
            "pkgroot",
            "pkgname",
            "pkgtype",
            "id",
            "version",
            "infofile",
            "scripts",
        ):
            if key not in request:
                if key in self.env:
                    request[key] = self.env[key]
                elif key in ["infofile", "scripts"]:
                    # these keys are optional, so empty string value is OK
                    request[key] = ""
                elif key == "pkgtype":
                    # we only support flat packages now
                    request[key] = "flat"
                else:
                    raise ProcessorError(f"Request key {key} missing")

        # Make sure chown array is present.
        if "chown" not in request:
            request["chown"] = []

        # Convert relative paths to absolute.
        for key, value in list(request.items()):
            if key in ("pkgroot", "pkgdir", "infofile", "scripts"):
                if value and not value.startswith("/"):
                    # search for it
                    request[key] = self.find_path_for_relpath(value)

        # Check for an existing flat package in the output dir and compare its
        # identifier and version to the one we're going to build.
        pkg_path = os.path.join(request["pkgdir"], request["pkgname"] + ".pkg")
        if self.pkg_already_exists(pkg_path, request["id"], request["version"]):
            self.output(
                "Existing package matches version and identifier, not building."
            )
            self.env["pkg_path"] = pkg_path
            self.env["new_package_request"] = False
            return

        # Send packaging request.
        try:
            self.output("Connecting")
            self.connect()
            self.output("Sending packaging request")
            self.env["new_package_request"] = True
            pkg_path = self.send_request(request)
        finally:
            self.output("Disconnecting")
            self.disconnect()

        # Return path to pkg.
        self.env["pkg_path"] = pkg_path
        self.env["pkg_creator_summary_result"] = {
            "summary_text": "The following packages were built:",
            "report_fields": ["identifier", "version", "pkg_path"],
            "data": {
                "identifier": request["id"],
                "version": request["version"],
                "pkg_path": pkg_path,
            },
        }

    def connect(self) -> None:
        """Connect to autopkgserver"""
        try:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket.connect(AUTO_PKG_SOCKET)
        except OSError as err:
            raise ProcessorError(
                "Unable to contact autopkgserver socket. "
                "The launchd com.github.autopkg.autopkgserver is most likely not "
                "loaded or running."
                f"\nError message: {err.strerror}"
            )

    def send_request(self, request) -> str:
        """Send a packaging request to the autopkgserver"""
        self.socket.send(plistlib.dumps(request))
        with self.socket.makefile(mode="r") as fileref:
            reply = fileref.read()
        if reply.startswith("OK:"):
            return reply.replace("OK:", "").rstrip()
        errors = reply.rstrip().split("\n")
        if not errors:
            errors = ["ERROR:No reply from server (crash?), check system logs"]
        raise ProcessorError(", ".join([s.replace("ERROR:", "") for s in errors]))

    def disconnect(self) -> None:
        """Disconnect from the autopkgserver"""
        try:
            self.socket.close()
        except OSError as e:
            self.output(f"Failed to close socket: {e}", verbose_level=2)

    def main(self) -> None:
        """Package something!"""
        self.package()


if __name__ == "__main__":
    PROCESSOR = PkgCreator()
    PROCESSOR.execute_shell()
