#!/usr/bin/env python
#
# Copyright 2014 Paul Suh
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


import os
import FoundationPlist
import tempfile
import shutil
import subprocess
from xml.etree.ElementTree import ElementTree 
from xml.etree.ElementTree import Element

from autopkglib.DmgMounter import DmgMounter
from autopkglib.FlatPkgUnpacker import FlatPkgUnpacker

from autopkglib import Processor, ProcessorError


__all__ = ["FlatPkgVersioner"]


class FlatPkgVersioner(FlatPkgUnpacker):
    description = ( "Looks inside a flat pkg to extract version information. ", 
                    "The pkg must not have inner packages, or the version information",
                    "will be ambiguous and the class will be unable to extract the version. ",
                    "If you have a flat package with inner packages, unpack the outer", 
                    "package and point this class to one of the inner packages." )
    input_variables = {
        "pkg_path": {
            "required": True,
            "description": 
                "Path to a package, may be inside a dmg. ",
        }
    }
    output_variables = {
        "version": {
            "description": "Version of the package"
        }
    }
    __doc__ = description
    

def readVersion( self, pkg_path ):

    # unpack the package to get at the PackageInfo file
    temp_path = tempfile.mkdtemp(prefix="autopkg", dir="/private/tmp")
    
    self.env["destination_path"] = tempfile.mkdtemp(prefix="autopkg", dir="/private/tmp")
    self.env["skip_payload"] = True
    
    self.unpackFlatPkg()
    
    # read the "version" attribute from the top level of the PackageInfo file
    try:
        with open(self.env['destination_path'] + "/PackageInfo", "r") as f:
            filedata = f.read(self.env['file_content'])
    except BaseException as e:
        raise ProcessorError("Can't read file at %s: %s" % (
                                self.env['destination_path'] + "/PackageInfo",
                                e))

    xmldata = ElementTree.fromstring( filedata )
    



def main(self):
    # Check if we're trying to copy something inside a dmg.
    (dmg_path, dmg, dmg_source_path) = self.env[
        'flat_pkg_path'].partition(".dmg/")
    dmg_path += ".dmg"
    try:
        if dmg:
            # Mount dmg and copy path inside.
            mount_point = self.mount(dmg_path)
            self.source_path = glob(
                os.path.join(mount_point, dmg_source_path))[0]
        else:
            # Straight copy from file system.
            self.source_path = self.env['flat_pkg_path']
        
        self.readVersion()
        
        self.output("Unpacked %s to %s" 
            % (self.source_path, self.env['destination_path']))
    finally:
        if dmg:
            self.unmount(dmg_path)

if __name__ == '__main__':
    processor = FlatPkgVersioner()
    processor.execute_shell()

