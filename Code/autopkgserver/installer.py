#!/usr/local/autopkg/python
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
"""Runs installer to install a package. Can install a package located inside a
disk image file."""

import subprocess


class InstallerError(Exception):
    """Base error for Installer errors"""

    pass


class Installer:
    """Runs /usr/sbin/installer to install a package"""

    def __init__(self, log, socket, request):
        """Arguments:

        log     A logger instance.
        socket  The socket for the requesting object
        request A request in plist format.
        """

        self.log = log
        self.socket = socket
        self.request = request

    def verify_request(self):
        """Make sure copy request has everything we need"""
        self.log.debug("Verifying install request")
        for key in ["package"]:
            if key not in self.request:
                raise InstallerError(f"ERROR:No {key} in request")

    def do_install(self):
        """Call /usr/sbin/installer"""
        pkg_path = self.request["package"]
        try:
            cmd = ["/usr/sbin/installer", "-verboseR", "-pkg", pkg_path, "-target", "/"]
            proc = subprocess.Popen(
                cmd,
                shell=False,
                bufsize=-1,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            while True:
                output = proc.stdout.readline()
                if not output and (proc.poll() is not None):
                    break
                self.socket.send(f"STATUS:{output.encode('UTF-8')}")
                self.log.info(output.rstrip())

            if proc.returncode != 0:
                raise InstallerError(f"ERROR:{proc.returncode}\n")
            self.log.info("install request completed.")
            return True
        except BaseException as err:
            self.log.error(f"Install failed: {err}")
            raise InstallerError(f"ERROR:{err}\n")

    def install(self):
        """Main method."""
        try:
            self.verify_request()
            self.do_install()
        except BaseException as err:
            raise InstallerError(err)
