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
import shutil

from glob import glob
from autopkglib import Processor, ProcessorError
from DmgMounter import DmgMounter


__all__ = ["Copier"]


class Copier(DmgMounter):
    description = "Copies source_path to destination_path."
    input_variables = {
        "source_path": {
            "required": True,
            "description": "Path to a file or directory to copy. " + \
                "Can point to a glob path inside a .dmg which will be mounted.",
        },
        "destination_path": {
            "required": True,
            "description": "Path to destination.",
        },
        "overwrite": {
            "required": False,
            "description": "Whether the destination will be overwritten if necessary.",
        },
    }
    output_variables = {
    }
    
    __doc__ = description
    
    def copy(self, source_item, dest_item, overwrite=False):
        '''Copies source_item to dest_item, overwriting if allowed'''
        # Remove destination if needed.
        if os.path.exists(dest_item) and overwrite:
            try:
                if os.path.isdir(dest_item) and not os.path.islink(dest_item):
                    shutil.rmtree(dest_item)
                else:
                    os.unlink(dest_item)
            except OSError, err:
                raise ProcessorError(
                    "Can't remove %s: %s" % (dest_item, err.strerror))
                    
        # Copy file or directory.
        try:
            if os.path.isdir(source_item):
                shutil.copytree(source_item, dest_item, symlinks=True)
            elif not os.path.isdir(dest_item):
                shutil.copyfile(source_item, dest_item)
            else:
                shutil.copy(source_item, dest_item)
            self.output("Copied %s to %s" % (source_item, dest_item))
        except BaseException, err:
            raise ProcessorError(
                "Can't copy %s to %s: %s" % (source_item, dest_item, err))
    
    def main(self):
        # Check if we're trying to copy something inside a dmg.
        (dmg_path, dmg,
         dmg_source_path) = self.env['source_path'].partition(".dmg/")
        dmg_path += ".dmg"
        try:
            if dmg:
                # Mount dmg and copy path inside.
                mount_point = self.mount(dmg_path)
                source_path = glob(
                    os.path.join(mount_point, dmg_source_path))[0]
            else:
                # Straight copy from file system.
                source_path = self.env['source_path']

            # do the copy
            self.copy(source_path, self.env['destination_path'],
                      overwrite=self.env.get("overwrite"))
        finally:
            if dmg:
                self.unmount(dmg_path)
    

if __name__ == '__main__':
    processor = Copier()
    processor.execute_shell()
    
