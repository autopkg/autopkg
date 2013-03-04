#!/usr/bin/env python
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


import os.path
import socket
import plistlib

from Processor import Processor, ProcessorError


AUTO_PKG_SOCKET = "/var/run/autopkgserver"


__all__ = ["PkgCreator"]


class PkgCreator(Processor):
    description = "Calls autopkgserver to create a package."
    input_variables = {
        "template_path": {
            "required": False,
            "description": "A package request template.",
        },
        "pkgroot": {
            "required": False,
            "description": "Virtual root of the package.",
        },
        "pkgdir": {
            "required": False,
            "description": "Output directory for the pkg.",
        },
        "pkgname": {
            "required": False,
            "description": "Name of the pkg, without the .pkg extension.",
        },
        "pkgtype": {
            "required": False,
            "description": "'bundle' or 'flat'.",
        },
        "id": {
            "required": False,
            "description": "Package bundle ID.",
        },
        "version": {
            "required": False,
            "description": "Package version.",
        },
        "infofile": {
            "required": False,
            "description": "Path to a package info file.",
        },
        "resources": {
            "required": False,
            "description": "Path to a Resources directory.",
        },
        "options": {
            "required": False,
            "description": "Space delimited string of packaging options.",
        },
    }
    output_variables = {
        "pkg_path": {
            "description": "The created package.",
        },
    }
    
    __doc__ = description
    
    def main(self):
        # Populate request with values from the template if given. Relative
        # paths are converted to absolute.
        if "template_path" in self.env:
            try:
                request = plistlib.readPlist(self.env['template_path'])
            except BaseException as e:
                raise ProcessorError("Malformed plist template %s" % self.env['template_path'])
            base_dir = os.path.dirname(os.path.abspath(self.env['template_path']))
            # Convert relative paths to absolute.
            for key, value in request.items():
                if key in ("pkgroot", "pkgdir", "infofile", "resources"):
                    if not value.startswith("/"):
                        # Relative to template directory.
                        value = os.path.normpath(os.path.join(base_dir, value))
                request[key] = value
        else:
            request = dict()
        
        # Set variables, and check that all keys are in request.
        for key in ("pkgroot",
                    "pkgdir",
                    "pkgname",
                    "pkgtype",
                    "id",
                    "version",
                    "infofile",
                    "resources",
                    "options"):
            if key in self.env:
                request[key] = self.env[key]
            else:
                if not key in request:
                    raise ProcessorError("Request key %s missing" % key)
        
        # Make sure chown dict is present.
        if not "chown" in request:
            request["chown"] = dict()
        
        # Convert relative paths to absolute.
        for key, value in request.items():
            if key in ("pkgroot", "pkgdir", "infofile", "resources"):
                if not value.startswith("/"):
                    # Relative to current directory.
                    request[key] = os.path.normpath(os.path.join(os.getcwdu(), value))
        
        # Send packaging request.
        try:
            print "Connecting"
            self.connect()
            print "Sending packaging request"
            pkg_path = self.send_request(request)
        finally:
            print "Disconnecting"
            self.disconnect()
        
        # Return path to pkg.
        self.env["pkg_path"] = pkg_path
    
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket.connect(AUTO_PKG_SOCKET)
        except socket.error as e:
            raise ProcessorError("Couldn't connect to autopkgserver: %s" % e.strerror)
    
    def send_request(self, request):
        self.socket.send(plistlib.writePlistToString(request))
        with os.fdopen(self.socket.fileno()) as f:
            reply = f.read()
        
        if reply.startswith("OK:"):
            return reply.replace("OK:", "").rstrip()
        
        errors = reply.rstrip().split("\n")
        if not errors:
            errors = ["ERROR:No reply from server (crash?), check system logs"]
        raise ProcessorError(", ".join([s.replace("ERROR:", "") for s in errors]))
    
    def disconnect(self):
        self.socket.close()
    

if __name__ == '__main__':
    processor = PkgCreator()
    processor.execute_shell()
    
