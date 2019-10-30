#!/Library/AutoPkg/Python3/Python.framework/Versions/Current/bin/python3
#
# Copyright 2016 Greg Neagle
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
"""See docstring for AppPkgCreator class"""

import os.path
import plistlib
import shutil
from glob import glob

from autopkglib import ProcessorError
from autopkglib.DmgMounter import DmgMounter
from autopkglib.PkgCreator import PkgCreator

__all__ = ["AppPkgCreator"]


class AppPkgCreator(DmgMounter, PkgCreator):
    """Calls autopkgserver to create a package from an application."""

    description = __doc__
    input_variables = {
        "app_path": {
            "required": False,
            "description": (
                "Path to an application to be packaged. Can be on a disk "
                "image and globbed. If not set, defaults to %pathname%/*.app. "
                "Typically %pathname% points to a disk image downloaded in a "
                "prior recipe step."
            ),
        },
        "pkg_path": {
            "required": False,
            "description": "The pathname for the pkg to be created. If not set, defaults "
            "to %RECIPE_CACHE_DIR%/%app_name%-%version%.pkg",
        },
        "bundleid": {
            "required": False,
            "description": "Bundle identifier of the app. If not set, will be extracted "
            "from the CFBundleIdentifier in the app's Info.plist.",
        },
        "version": {
            "required": False,
            "description": "Version of the app. If not set, will be extracted from the "
            "CFBundleShortVersionString in the app's Info.plist.",
        },
        "force_pkg_build": {
            "required": False,
            "description": (
                "When set, this forces building a new package even if "
                "a package already exists in the output directory with "
                "the same identifier and version number. Defaults to False"
            ),
        },
    }
    output_variables = {
        "new_package_request": {
            "description": "True if a new package was actually requested to be built. "
            "False if a package with the same filename, identifier and "
            "version already exists and thus no package was built (see "
            "'force_pkg_build' input variable.)"
        },
        "version": {"description": "Version of the app."},
        "app_pkg_creator_summary_result": {
            "description": "Description of interesting results."
        },
    }

    def read_info_plist(self, app_path):
        """Read Contents/Info.plist from the app."""
        # pylint: disable=no-self-use
        plistpath = os.path.join(app_path, "Contents", "Info.plist")
        try:
            with open(plistpath, "rb") as f:
                plist = plistlib.load(f)
        except Exception as err:
            raise ProcessorError("Can't read %s: %s" % (plistpath, err))
        return plist

    def package_app(self, app_path):
        """Build a packaging request, send it to the autopkgserver and get the
        constructed package."""

        # clear any pre-exising summary result
        if "app_pkg_creator_summary_result" in self.env:
            del self.env["app_pkg_creator_summary_result"]

        # get version and bundleid
        infoplist = self.read_info_plist(app_path)
        if not self.env.get("version"):
            try:
                self.env["version"] = infoplist["CFBundleShortVersionString"]
                self.output("Version: %s" % self.env["version"])
            except BaseException as err:
                raise ProcessorError(err)
        if not self.env.get("bundleid"):
            try:
                self.env["bundleid"] = infoplist["CFBundleIdentifier"]
                self.output("BundleID: %s" % self.env["bundleid"])
            except BaseException as err:
                raise ProcessorError(err)

        # get pkgdir and pkgname
        if self.env.get("pkg_path"):
            pkg_path = self.env["pkg_path"]
            pkgdir = os.path.dirname(pkg_path)
            pkgname = os.path.splitext(os.path.basename(pkg_path))[0]
        else:
            pkgdir = self.env["RECIPE_CACHE_DIR"]
            pkgname = "%s-%s" % (
                os.path.splitext(os.path.basename(app_path))[0],
                self.env["version"],
            )
            pkg_path = os.path.join(pkgdir, pkgname + ".pkg")

        # Check for an existing flat package in the output dir and compare
        # its identifier and version to the one we're going to build.
        if self.pkg_already_exists(pkg_path, self.env["bundleid"], self.env["version"]):
            self.output(
                "Existing package matches version and identifier, " "not building."
            )
            self.env["pkg_path"] = pkg_path
            self.env["new_package_request"] = False
            return

        # create pkgroot and copy application into it
        pkgroot = os.path.join(self.env["RECIPE_CACHE_DIR"], "payload")
        if os.path.exists(pkgroot):
            # remove it if it already exists
            try:
                if os.path.isdir(pkgroot) and not os.path.islink(pkgroot):
                    shutil.rmtree(pkgroot)
                else:
                    os.unlink(pkgroot)
            except OSError as err:
                raise ProcessorError("Can't remove %s: %s" % (pkgroot, err.strerror))
        try:
            os.makedirs(os.path.join(pkgroot, "Applications"), 0o775)
        except OSError as err:
            raise ProcessorError("Could not create pkgroot: %s" % err.strerror)

        app_name = os.path.basename(app_path)
        source_item = app_path
        dest_item = os.path.join(pkgroot, "Applications", app_name)
        try:
            if os.path.isdir(source_item):
                shutil.copytree(source_item, dest_item, symlinks=True)
            elif not os.path.isdir(dest_item):
                shutil.copyfile(source_item, dest_item)
            else:
                shutil.copy(source_item, dest_item)
            self.output("Copied %s to %s" % (source_item, dest_item))
        except OSError as err:
            raise ProcessorError(
                "Can't copy %s to %s: %s" % (source_item, dest_item, err.strerror)
            )

        # build a package request
        request = {
            "pkgroot": pkgroot,
            "pkgdir": pkgdir,
            "pkgname": pkgname,
            "pkgtype": "flat",
            "id": self.env["bundleid"],
            "version": self.env["version"],
            "infofile": "",
            "resources": "",
            "chown": [{"path": "Applications", "user": "root", "group": "admin"}],
            "scripts": "",
        }

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
        self.env["app_pkg_creator_summary_result"] = {
            "summary_text": "The following packages were built:",
            "report_fields": ["identifier", "version", "pkg_path"],
            "data": {
                "identifier": request["id"],
                "version": request["version"],
                "pkg_path": pkg_path,
            },
        }

    def main(self):
        """Find an app, package it up"""
        if self.env.get("app_path"):
            app_path = self.env["app_path"]
        elif self.env.get("pathname"):
            app_path = self.env["pathname"] + "/*.app"
        else:
            raise ProcessorError("No app_path or pathname specified.")
        # Check if we're trying to package something inside a dmg.
        (dmg_path, dmg, dmg_app_path) = self.parsePathForDMG(app_path)
        try:
            if dmg:
                # Mount dmg and return path inside.
                mount_point = self.mount(dmg_path)
                app_path = os.path.join(mount_point, dmg_app_path)
            # process path with glob.glob
            matches = glob(app_path)
            if len(matches) == 0:
                raise ProcessorError(
                    "Error processing path '%s' with glob. " % app_path
                )
            matched_app_path = matches[0]
            if len(matches) > 1:
                self.output(
                    "WARNING: Multiple paths match 'app_path' glob '%s':" % app_path
                )
                for match in matches:
                    self.output("  - %s" % match)

            if [c for c in "*?[]!" if c in app_path]:
                self.output(
                    "Using path '%s' matched from globbed '%s'."
                    % (matched_app_path, app_path)
                )

            # do the copy
            self.package_app(matched_app_path)

        finally:
            if dmg:
                self.unmount(dmg_path)


if __name__ == "__main__":
    PROCESSOR = AppPkgCreator()
    PROCESSOR.execute_shell()
