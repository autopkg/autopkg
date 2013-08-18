#!/usr/bin/env python
#
# Copyright 2013 Greg Neagle
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

from autopkglib import Processor, ProcessorError
from Copier import Copier


__all__ = ["PkgCopier"]


class PkgCopier(Copier):
    description = "Copies source_pkg to pkg_path."
    input_variables = {
        "source_path": {
            "required": True,
            "description": "Path to a pkg to copy. " + \
                "Can point to a path inside a .dmg which will be mounted.",
        },
        "pkg_path": {
            "required": True,
            "description": "Path to destination.",
        },
    }
    output_variables = {
        "pkg_path": {
            "description": "Path to copied pkg.",
        },
    }

    __doc__ = description
    
    def main(self):
        # Check if we're trying to copy something inside a dmg.
        (dmg_path, dmg,
         dmg_source_path) = self.env['source_path'].partition(".dmg/")
        dmg_path += ".dmg"
        try:
            if dmg:
                # Mount dmg and copy path inside.
                mount_point = self.mount(dmg_path)
                source_path = os.path.join(mount_point, dmg_source_path)
            else:
                # Straight copy from file system.
                source_path = self.env['source_path']

            # do the copy
            pkg_path = self.env["pkg_path"]
            self.copy(source_path, pkg_path, overwrite=True)

        finally:
            if dmg:
                self.unmount(dmg_path)
    

if __name__ == '__main__':
    processor = Copier()
    processor.execute_shell()
