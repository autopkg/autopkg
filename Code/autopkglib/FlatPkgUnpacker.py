#!/usr/bin/python
#
# Copyright 2013 Timothy Sutton
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

# Borrowed code and concepts from Unzipper and Copier processors.

import os.path
import subprocess
import shutil

from glob import glob
from autopkglib import ProcessorError
from DmgMounter import DmgMounter


__all__ = ["FlatPkgUnpacker"]


class FlatPkgUnpacker(DmgMounter):
    description = ("Expands a flat package using pkgutil or xar. "
        "For xar it also optionally skips extracting the payload.")
    input_variables = {
        "flat_pkg_path": {
            "required": True,
            "description": ("Path to a flat package. "
                "Can point to a globbed path inside a .dmg which will "
                "be mounted."),
        },
        "skip_payload": {
            "required": False,
            "description": ("If true, 'Payload' files will be skipped. "
                "Defaults to False. Note if this option is used then the "
                "files are extracted using xar(1) instead of pkgutil(1). "
                "This means components of the package will not be "
                "extracted such as scripts."),
        },
        "destination_path": {
            "required": True,
            "description": ("Directory where archive will be unpacked, created "
                "if necessary."),
        },
        "purge_destination": {
            "required": False,
            "description": ("Whether the contents of the destination directory "
                "will be removed before unpacking. Note that unless "
                "skip_payload argument is used the destination directory "
                "will be removed as pkgutil requires an empty destination."),
        },
    }
    output_variables = {
    }

    __doc__ = description
    source_path = None

    def unpackFlatPkg(self):
        # Create the directory if needed.
        if not os.path.exists(self.env['destination_path']):
            try:
                os.mkdir(self.env['destination_path'])
            except OSError as e:
                raise ProcessorError("Can't create %s: %s" 
                    % (self.env['destination_path'], e.strerror))
        elif self.env.get('purge_destination'):
            for entry in os.listdir(self.env['destination_path']):
                path = os.path.join(self.env['destination_path'], entry)
                try:
                    if os.path.isdir(path) and not os.path.islink(path):
                        shutil.rmtree(path)
                    else:
                        os.unlink(path)
                except OSError as e:
                    raise ProcessorError(
                        "Can't remove %s: %s" % (path, e.strerror))

        if self.env.get('skip_payload'):
            self.xarExpand()
        else:
            self.pkgutilExpand()

    def xarExpand(self):
        try:
            xarcmd = ["/usr/bin/xar",
                      "-x",
                      "-C", self.env['destination_path'],
                      "-f", self.source_path]
            if self.env.get('skip_payload'):
                xarcmd.extend(["--exclude", "Payload"])
            p = subprocess.Popen(xarcmd,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            (out, err) = p.communicate()
        except OSError as e:
            raise ProcessorError("xar execution failed with error code %d: %s" 
                % (e.errno, e.strerror))
        if p.returncode != 0:
            raise ProcessorError("extraction of %s with xar failed: %s" 
                % (self.env['flat_pkg_path'], err))

    def pkgutilExpand(self):
        # pkgutil requires the dest. folder to be non-existant
        if os.path.exists(self.env['destination_path']):
            try:
                shutil.rmtree(self.env['destination_path'])
            except OSError as e:
                raise ProcessorError(
                    "Can't remove %s: %s" % (self.env['destination_path'], e.strerror))

        try:
            pkgutilcmd = ["/usr/sbin/pkgutil",
                      "--expand",
                      self.source_path,
                      self.env['destination_path']]
            p = subprocess.Popen(pkgutilcmd,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            (out, err) = p.communicate()
        except OSError as e:
            raise ProcessorError("pkgutil execution failed with error code %d: %s" 
                % (e.errno, e.strerror))
        if p.returncode != 0:
            raise ProcessorError("extraction of %s with pkgutil failed: %s" 
                % (self.env['flat_pkg_path'], err))

    def main(self):
        # Check if we're trying to copy something inside a dmg.
        (dmg_path, dmg, dmg_source_path) = self.parsePathForDMG(
                                            self.env['flat_pkg_path'])
        try:
            if dmg:
                # Mount dmg and copy path inside.
                mount_point = self.mount(dmg_path)
                self.source_path = glob(
                    os.path.join(mount_point, dmg_source_path))[0]
            else:
                # Straight copy from file system.
                self.source_path = self.env['flat_pkg_path']
            self.unpackFlatPkg()
            self.output("Unpacked %s to %s" 
                % (self.source_path, self.env['destination_path']))
        finally:
            if dmg:
                self.unmount(dmg_path)


if __name__ == '__main__':
    processor = FlatPkgUnpacker()
    processor.execute_shell()
    
