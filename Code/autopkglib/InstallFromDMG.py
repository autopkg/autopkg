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
"""See docstring for InstallFromDMG class"""

import os.path
import socket
import FoundationPlist

from autopkglib import ProcessorError
from autopkglib.DmgMounter import DmgMounter


AUTOPKGINSTALLD_SOCKET = "/var/run/autopkginstalld"


__all__ = ["InstallFromDMG"]


class InstallFromDMG(DmgMounter):
    """Calls autopkginstalld to copy items from a disk image to the root
    filesystem."""
    description = __doc__
    input_variables = {
        "dmg_path": {
            "required": True,
            "description": "Path to the disk image."
        },
        "items_to_copy": {
            "required": True,
            "description": (
                "Array of dictionaries describing what is to be copied. "
                "Each item should contain 'source_path' and "
                "'destination_path', and may optionally include: "
                "'destination_item' to rename the item on copy, and "
                "'user', 'group' and 'mode' to explictly set those items.")
        },
        "download_changed": {
            "required": False,
            "description": (
                "download_changed is set by the URLDownloaded processor to "
                "indicate that a new file was downloaded. If this key is set "
                "in the environment and is False or empty the installation "
                "will be skipped.")
        },
    }
    output_variables = {
        "install_result": "Result of install request."
    }

    def install(self):
        '''Build an ItemCopier request, send it to autopkginstalld'''

        if "download_changed" in self.env:
            if not self.env["download_changed"]:
                # URLDownloader did not download something new, 
                # so skip the install
                self.output("Skipping installation: no new download.")
                self.env["install_result"] = "OK:SKIPPED"
                return
        try:
            mount_point = self.mount(self.env['dmg_path'])

            request = {'mount_point': mount_point,
                       'items_to_copy': self.env["items_to_copy"]}
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
            self.unmount(self.env['dmg_path'])

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
    PROCESSOR = InstallFromDMG()
    PROCESSOR.execute_shell()

