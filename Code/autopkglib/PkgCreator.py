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
import FoundationPlist
import subprocess
import xml.etree.ElementTree as ET

from autopkglib import Processor, ProcessorError


AUTO_PKG_SOCKET = "/var/run/autopkgserver"


__all__ = ["PkgCreator"]


class PkgCreator(Processor):
    description = "Calls autopkgserver to create a package."
    input_variables = {
        "pkg_request": {
            "required": True,
            "description": ("A package request dictionary. See "
                            "Code/autopkgserver/autopkgserver for more details.")
        },
        "force_pkg_build": {
            "required": False,
            "description": ("When set, this forces building a new package even if "
                            "a package already exists in the output directory with "
                            "the same identifier and version number. Defaults to "
                            "False."),
        },
    }
    output_variables = {
        "pkg_path": {
            "description": "The created package.",
        },
        "new_package_request": {
            "description": ("True if a new package was actually requested to be built. "
                            "False if a package with the same filename, identifier and "
                            "version already exists and thus no package was built (see "
                            "'force_pkg_build' input variable.")
        },
    }
    
    __doc__ = description




    def find_path_for_relpath(self, relpath):
        '''Searches for the relative path.
        Search order is:
            RECIPE_CACHE_DIR
            RECIPE_DIR
            PARENT_RECIPE directories'''
        cache_dir = self.env.get('RECIPE_CACHE_DIR')
        recipe_dir = self.env.get('RECIPE_DIR')
        search_dirs = [cache_dir, recipe_dir]
        if self.env.get("PARENT_RECIPES"):
            # also look in the directories containing the parent recipes
            parent_recipe_dirs = list(set([
                os.path.dirname(item)
                for item in self.env["PARENT_RECIPES"]]))
            search_dirs.extend(parent_recipe_dirs)
        for directory in search_dirs:
            test_item = os.path.join(directory, relpath)
            if os.path.exists(test_item):
                return os.path.normpath(test_item)

        raise ProcessorError("Can't find %s" % relpath)
    
    def xarExpand(self, source_path):
        try:
            xarcmd = ["/usr/bin/xar",
                      "-x",
                      "-C", self.env.get('RECIPE_CACHE_DIR'),
                      "-f", source_path,
                      "PackageInfo"]
            p = subprocess.Popen(xarcmd,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            (out, err) = p.communicate()
        except OSError as e:
            raise ProcessorError("xar execution failed with error code %d: %s" 
                % (e.errno, e.strerror))
        if p.returncode != 0:
            raise ProcessorError("extraction of %s with xar failed: %s" 
                % (source_path, err))

    
    def package(self):
        request = self.env["pkg_request"]
        if not 'pkgdir' in request:
            request['pkgdir'] = self.env['RECIPE_CACHE_DIR']
        
        # Set variables, and check that all keys are in request.
        for key in ("pkgroot",
                    "pkgname",
                    "pkgtype",
                    "id",
                    "version",
                    "infofile",
                    "resources",
                    "options",
                    "scripts"):
            if not key in request:
                if key in self.env:
                    request[key] = self.env[key]
                elif key in ["infofile", "resources", "options", "scripts"]:
                    # these keys are optional, so empty string value is OK
                    request[key] = ""
                elif key == "pkgtype":
                    # we only support flat packages now
                    request[key] = "flat"
                else:
                    raise ProcessorError("Request key %s missing" % key)
        
        # Make sure chown dict is present.
        if not "chown" in request:
            request["chown"] = dict()
        
        # Convert relative paths to absolute.
        for key, value in request.items():
            if key in ("pkgroot", "pkgdir", "infofile", "resources", "scripts"):
                if value and not value.startswith("/"):
                    # search for it
                    request[key] = self.find_path_for_relpath(value)

        
        # Check for an existing flat package in the output dir and compare its
        # identifier and version to the one we're going to build.
        pkg_path = os.path.join(request['pkgdir'], request['pkgname'] + '.pkg')
        if os.path.exists(pkg_path) and not self.env.get("force_pkg_build"):
            self.output("Package already exists at path %s." % pkg_path)
            self.xarExpand(pkg_path)
            packageinfo_file = os.path.join(self.env['RECIPE_CACHE_DIR'], 'PackageInfo')
            if not os.path.exists(packageinfo_file):
                raise ProcessorError(
                    "Failed to parse existing package, as no PackageInfo "
                    "file count be found in the extracted archive.")
                
            tree = ET.parse(packageinfo_file)
            root = tree.getroot()
            local_version = root.attrib['version']
            local_id = root.attrib['identifier']

            if (local_version == request['version']) and (local_id == request['id']):
                    self.output("Existing package matches version and identifier, not building.")
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
    
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket.connect(AUTO_PKG_SOCKET)
        except socket.error as e:
            raise ProcessorError("Couldn't connect to autopkgserver: %s" % e.strerror)
    
    def send_request(self, request):
        self.socket.send(FoundationPlist.writePlistToString(request))
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
        
    def main(self):
        self.package()
    

if __name__ == '__main__':
    processor = PkgCreator()
    processor.execute_shell()
    
