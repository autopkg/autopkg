#!/usr/bin/python
#
# Copyright 2014 Greg Neagle
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
"""See docstring for Installer class"""

import os.path
import socket
import FoundationPlist

from glob import glob
from autopkglib import ProcessorError
from autopkglib.DmgMounter import DmgMounter

AUTOPKGINSTALLD_SOCKET = "/var/run/autopkginstalld"


__all__ = ["Installer"]


class Installer(DmgMounter):
    """Calls autopkginstalld to install a package."""
    description = __doc__
    input_variables = {
        "pkg_path": {
            "required": True,
            "description": (
                "Path to the package to be installed. Can be inside a disk "
                "image.")
        },
        "new_package_request": {
            "required": False,
            "description": (
                "new_package_request is set by the PkgCreator processor to "
                "indicate that a new package was built. If this key is set in "
                "the environment and is False or empty the installation will be"
                "skipped.")
        },
        "download_changed": {
            "required": False,
            "description": (
                "download_changed is set by the URLDownloaded processor to "
                "indicate that a new file was downloaded. If this key is set "
                "in the environment and is False or empty the installation "
                "will be skipped, unless new_package_request is non-False.")
        },
    }
    output_variables = {
        "install_result": "Result of install request."
    }

    def install(self):
        '''Build an installation request, send it to autopkginstalld'''

        if "new_package_request" in self.env:
            if not self.env["new_package_request"]:
                # PkgCreator did not build a new package, so skip the install
                self.output("Skipping installation: no new package.")
                self.env["install_result"] = "OK:SKIPPED"
                return
        elif "download_changed" in self.env:
            if not self.env["download_changed"]:
                # URLDownloader did not download something new,
                # so skip the install
                self.output("Skipping installation: no new download.")
                self.env["install_result"] = "OK:SKIPPED"
                return

        pkg_path = self.env["pkg_path"]
        # Check if we're trying to copy something inside a dmg.
        (dmg_path, dmg, dmg_pkg_path) = self.parsePathForDMG(pkg_path)
        try:
            if dmg:
                # Mount dmg and copy path inside.
                mount_point = self.mount(dmg_path)
                pkg_path = os.path.join(mount_point, dmg_pkg_path)
            # process path with glob.glob
            matches = glob(pkg_path)
            if len(matches) == 0:
                raise ProcessorError(
                    "Error processing path '%s' with glob. " % pkg_path)
            matched_pkg_path = matches[0]
            if len(matches) > 1:
                self.output(
                    "WARNING: Multiple paths match 'pkg_path' glob '%s':"
                    % pkg_path)
                for match in matches:
                    self.output("  - %s" % match)

            if [c for c in '*?[]!' if c in pkg_path]:
                self.output("Using path '%s' matched from globbed '%s'."
                            % (matched_pkg_path, pkg_path))

            request = {'package': matched_pkg_path}
            result = None
            # Send install request.
            try:
                self.output("Connecting")
                self.connect()
                self.output("Sending installation request")
                result = self.send_request(request)
            except BaseException as err:
                result = "ERROR: %s" % repr(err)
            finally:
                self.output("Disconnecting")
                self.disconnect()

            # Return result.
            self.output("Result: %s" % result)
            self.env["install_result"] = result

        finally:
            if dmg:
                self.unmount(dmg_path)

    def connect(self):
        '''Connect to autopkginstalld'''
        try:
            #pylint: disable=attribute-defined-outside-init
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            #pylint: enable=attribute-defined-outside-init
            self.socket.connect(AUTOPKGINSTALLD_SOCKET)
        except socket.error as err:
            raise ProcessorError(
                "Couldn't connect to autopkginstalld: %s" % err.strerror)

    def send_request(self, request):
        '''Send an install request to autopkginstalld'''
        self.socket.send(FoundationPlist.writePlistToString(request))
        with os.fdopen(self.socket.fileno()) as fileref:
            while True:
                data = fileref.readline()
                if data:
                    if data.startswith("OK:"):
                        return data.replace("OK:", "").rstrip()
                    elif data.startswith("ERROR:"):
                        break
                    else:
                        self.output(data.rstrip())
                else:
                    break

        errors = data.rstrip().split("\n")
        if not errors:
            errors = ["ERROR:No reply from autopkginstalld (crash?), "
                      "check system logs"]
        raise ProcessorError(
            ", ".join([s.replace("ERROR:", "") for s in errors]))

    def disconnect(self):
        '''Disconnect from autopkginstalld'''
        self.socket.close()

    def main(self):
        '''Install something!'''
        self.install()


if __name__ == '__main__':
    PROCESSOR = Installer()
    PROCESSOR.execute_shell()

