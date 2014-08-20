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

from autopkglib import Processor, ProcessorError


AUTOPKGINSTALLD_SOCKET = "/var/run/autopkginstalld"


__all__ = ["Installer"]


class Installer(Processor):
    """Calls autopkginstalld to create a package."""
    description = __doc__
    input_variables = {
        "pkg_path": {
            "required": True,
            "description": "Path to the package to be installed."
        },
        "new_package_request": {
            "required": False,
            "description": (
                "new_package_request is set by the PkgCreator processor to "
                "indicate that a new package was built. If this key is set in "
                "the environment and is False or empty the installation will be"
                "skipped.")
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

        request = {'package': self.env["pkg_path"]}
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
        self.env["install_result"] = result

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

