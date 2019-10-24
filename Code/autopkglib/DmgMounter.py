#!/usr/bin/python
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

import plistlib
import subprocess
import sys

from autopkglib import Processor, ProcessorError, log, log_err


__all__ = ["DmgMounter"]


class DmgMounter(Processor):
    """Base class for Processors that need to mount disk images."""

    DMG_EXTENSIONS = [".dmg", ".iso", ".DMG", ".ISO"]

    def __init__(self, data=None, infile=None, outfile=None):
        super(DmgMounter, self).__init__(data, infile, outfile)
        self.mounts = dict()

    # pylint: disable=invalid-name
    def parsePathForDMG(self, pathname):
        """Helper method for working with paths that reference something
        inside a disk image"""
        for extension in self.DMG_EXTENSIONS:
            (dmg_path, dmg, dmg_source_path) = pathname.partition(extension + "/")
            if dmg:
                dmg_path += extension
                return dmg_path, dmg, dmg_source_path
        # no disk image in path
        return pathname, "", ""

    # pylint: enable=invalid-name

    def get_first_plist(self, text_string):
        """Gets the first plist from a text string that may contain one or
        more text-style plists.
        Returns a tuple - the first plist (if any) and the remaining
        string after the plist"""
        # pylint: disable=no-self-use

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
        has_sla = False
        proc = subprocess.Popen(
            ["/usr/bin/hdiutil", "imageinfo", dmgpath, "-plist"],
            bufsize=-1,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        (stdout, stderr) = proc.communicate()
        if stderr:
            # some error with hdiutil.
            # Output but return False so we can attempt to continue
            self.output("hdiutil imageinfo error %s with image %s." % (stderr, dmgpath))
            return False

        (pliststr, stdout) = self.get_first_plist(stdout)
        if pliststr:
            try:
                plist = plistlib.loads(pliststr)
                properties = plist.get("Properties")
                if properties:
                    has_sla = properties.get("Software License Agreement", False)
            except Exception:
                pass

        return has_sla

    def mount(self, pathname):
        """Mount image with hdiutil."""
        # Make sure we don't try to mount something twice.
        if pathname in self.mounts:
            raise ProcessorError("%s is already mounted" % pathname)

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
            )
            (stdout, stderr) = proc.communicate(stdin)
        except OSError as err:
            raise ProcessorError(
                "hdiutil execution failed with error code %d: %s"
                % (err.errno, err.strerror)
            )
        if proc.returncode != 0:
            raise ProcessorError("mounting %s failed: %s" % (pathname, stderr))

        # Read output plist.
        (pliststr, stdout) = self.get_first_plist(stdout)
        try:
            output = plistlib.loads(pliststr)
        except Exception:
            raise ProcessorError(
                "mounting %s failed: unexpected output from hdiutil" % pathname
            )

        # Find mount point.
        for part in output.get("system-entities", []):
            if "mount-point" in part:
                # Add to mount list.
                self.mounts[pathname] = part["mount-point"]
                self.output("Mounted disk image %s" % pathname)
                return self.mounts[pathname]
        raise ProcessorError(
            "mounting %s failed: unexpected output from hdiutil" % pathname
        )

    def unmount(self, pathname):
        """Unmount previously mounted image."""

        # Don't try to unmount something we didn't mount.
        if pathname not in self.mounts:
            raise ProcessorError("%s is not mounted" % pathname)

        # Call hdiutil.
        try:
            proc = subprocess.Popen(
                ("/usr/bin/hdiutil", "detach", self.mounts[pathname]),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stderr = proc.communicate()[1]
        except OSError as err:
            raise ProcessorError(
                "hdiutil execution failed with error code %d: %s"
                % (err.errno, err.strerror)
            )
        if proc.returncode != 0:
            raise ProcessorError("unmounting %s failed: %s" % (pathname, stderr))

        # Delete mount from mount list.
        del self.mounts[pathname]


if __name__ == "__main__":
    try:
        DMGMOUNTER = DmgMounter()
        MOUNTPOINT = DMGMOUNTER.mount("Download/Firefox-sv-SE.dmg")
        log("Mounted at %s" % MOUNTPOINT)
        DMGMOUNTER.unmount("Download/Firefox-sv-SE.dmg")
    except ProcessorError as err:
        log_err("ProcessorError: %s" % err)
        sys.exit(10)
    else:
        sys.exit(0)
