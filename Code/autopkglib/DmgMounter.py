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

"""See docstring for DmgMounter class"""

import glob
import os
import plistlib
import subprocess
import sys

from autopkglib import Processor, ProcessorError, is_mac, is_path_under, log, log_err

__all__ = ["DmgMounter"]


class DmgMounter(Processor):
    """Base class for Processors that need to mount disk images."""

    description = __doc__
    lifecycle = {"introduced": "0.1.0"}
    DMG_EXTENSIONS = [".dmg", ".iso", ".DMG", ".ISO"]

    def __init__(self, data=None, infile=None, outfile=None):
        super().__init__(data, infile, outfile)
        self.mounts = dict()

    def parsePathForDMG(self, pathname):
        """Helper method for working with paths that reference something
        inside a disk image"""
        for extension in self.DMG_EXTENSIONS:
            for separator in ("/", "\\"):
                dmg_path, dmg, dmg_source_path = pathname.partition(
                    extension + separator
                )
                if dmg:
                    dmg_path += extension
                    return dmg_path, dmg, dmg_source_path
        # no disk image in path
        return pathname, "", ""

    def path_in_mount(self, mount_point, dmg_source_path):
        """Return a path under mount_point for a DMG-relative path."""
        validation_path = dmg_source_path.replace("\\", "/")
        if validation_path.startswith("/"):
            raise ProcessorError(
                f"DMG path '{dmg_source_path}' must be relative to the mounted image."
            )
        if ".." in [part for part in validation_path.split("/") if part]:
            raise ProcessorError(
                f"DMG path '{dmg_source_path}' may not contain parent-directory references."
            )

        mounted_path = os.path.normpath(os.path.join(mount_point, dmg_source_path))
        if not is_path_under(mounted_path, mount_point):
            raise ProcessorError(
                f"DMG path '{dmg_source_path}' resolves outside the mounted image."
            )
        return mounted_path

    def validate_paths_in_mount(self, mount_point, paths):
        """Raise if any resolved path is outside mount_point."""
        for path in paths:
            if not is_path_under(path, mount_point):
                raise ProcessorError(
                    f"DMG path '{path}' resolves outside the mounted image."
                )

    def glob_paths_in_mount(self, mount_point, dmg_source_path, recursive=False):
        """Glob a DMG-relative path and ensure all matches stay in mount_point."""
        mounted_path = self.path_in_mount(mount_point, dmg_source_path)
        matches = glob.glob(mounted_path, recursive=recursive)
        self.validate_paths_in_mount(mount_point, matches)
        return mounted_path, matches

    def get_first_plist(self, text_string):
        """Gets the first plist from a text string that may contain one or
        more text-style plists.
        Returns a tuple - the first plist (if any) and the remaining
        string after the plist"""

        plist_header = "<?xml version"
        plist_footer = "</plist>"
        plist_start_index = text_string.find(plist_header)
        if plist_start_index == -1:
            # not found
            return ("", text_string)
        plist_end_index = text_string.find(
            plist_footer, plist_start_index + len(plist_header)
        )
        if plist_end_index == -1:
            # not found
            return ("", text_string)
        # adjust end value
        plist_end_index = plist_end_index + len(plist_footer)
        return (
            text_string[plist_start_index:plist_end_index],
            text_string[plist_end_index:],
        )

    def dmg_has_sla(self, dmgpath):
        """Returns true if dmg has a Software License Agreement.
        These dmgs normally cannot be attached without user intervention"""
        if not is_mac():
            raise ProcessorError(
                "Disk image mounting is only supported on macOS. "
                "The 'hdiutil' utility is not available on this platform."
            )

        has_sla = False
        try:
            proc = subprocess.Popen(
                ["/usr/bin/hdiutil", "imageinfo", dmgpath, "-plist"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = proc.communicate()
        except OSError as err:
            raise ProcessorError(
                f"hdiutil execution failed with error code {err.errno}: {err.strerror}"
            )
        if stderr:
            # some error with hdiutil. Print it, but try to continue anyway.
            # (APFS disk images generate extraneous output to stderr)
            self.output(f"hdiutil imageinfo error {stderr} with image {dmgpath}.")

        pliststr, stdout = self.get_first_plist(stdout)
        if pliststr:
            try:
                plist = plistlib.loads(pliststr.encode())
                properties = plist.get("Properties")
                if properties:
                    has_sla = properties.get("Software License Agreement", False)
            except Exception:
                pass

        return has_sla

    def mount(self, pathname):
        """Mount image with hdiutil."""
        if not is_mac():
            raise ProcessorError(
                "Disk image mounting is only supported on macOS. "
                "The 'hdiutil' utility is not available on this platform."
            )

        # Make sure we don't try to mount something twice.
        if pathname in self.mounts:
            raise ProcessorError(f"{pathname} is already mounted")

        stdin = ""
        if self.dmg_has_sla(pathname):
            stdin = "Y\n"

        # Call hdiutil.
        try:
            proc = subprocess.Popen(
                (
                    "/usr/bin/hdiutil",
                    "attach",
                    "-plist",
                    "-mountrandom",
                    "/private/tmp",
                    "-nobrowse",
                    pathname,
                ),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = proc.communicate(stdin)
        except OSError as err:
            raise ProcessorError(
                f"hdiutil execution failed with error code {err.errno}: {err.strerror}"
            )
        if proc.returncode != 0:
            raise ProcessorError(f"mounting {pathname} failed: {stderr}")

        # Read output plist.
        pliststr, stdout = self.get_first_plist(stdout)
        try:
            output = plistlib.loads(pliststr.encode())
        except Exception:
            raise ProcessorError(
                f"mounting {pathname} failed: unexpected output from hdiutil"
            )

        # Find mount point.
        for part in output.get("system-entities", []):
            if "mount-point" in part:
                # Add to mount list.
                self.mounts[pathname] = part["mount-point"]
                self.output(f"Mounted disk image {pathname}")
                return self.mounts[pathname]
        raise ProcessorError(
            f"mounting {pathname} failed: unexpected output from hdiutil"
        )

    def unmount(self, pathname) -> None:
        """Unmount previously mounted image."""
        if not is_mac():
            raise ProcessorError(
                "Disk image unmounting is only supported on macOS. "
                "The 'hdiutil' utility is not available on this platform."
            )

        # Don't try to unmount something we didn't mount.
        if pathname not in self.mounts:
            raise ProcessorError(f"{pathname} is not mounted")

        # Call hdiutil.
        try:
            proc = subprocess.Popen(
                ("/usr/bin/hdiutil", "detach", self.mounts[pathname]),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            _, stderr = proc.communicate()
        except OSError as err:
            raise ProcessorError(
                f"hdiutil execution failed with error code {err.errno}: {err.strerror}"
            )
        if proc.returncode != 0:
            raise ProcessorError(f"unmounting {pathname} failed: {stderr}")

        # Delete mount from mount list.
        del self.mounts[pathname]


if __name__ == "__main__":
    try:
        DMGMOUNTER = DmgMounter()
        MOUNTPOINT = DMGMOUNTER.mount("Download/Firefox-sv-SE.dmg")
        log(f"Mounted at {MOUNTPOINT}")
        DMGMOUNTER.unmount("Download/Firefox-sv-SE.dmg")
    except ProcessorError as err:
        log_err(f"ProcessorError: {err}")
        sys.exit(10)
    else:
        sys.exit(0)
