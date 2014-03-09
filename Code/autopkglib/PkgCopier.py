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
import glob

from autopkglib import Processor, ProcessorError
from Copier import Copier


__all__ = ["PkgCopier"]


class PkgCopier(Copier):
    description = "Copies source_pkg to pkg_path."
    input_variables = {
        "source_pkg": {
            "required": True,
            "description": ("Path to a pkg to copy. Can point to a path inside "
            "a .dmg which will be mounted. This path may also contain basic "
            "globbing characters such as the wildcard '*', but only the first "
            "result will be returned."),
        },
        "pkg_path": {
            "required": False,
            "description": 
                ("Path to destination. Defaults to "
                "RECIPE_CACHE_DIR/os.path.basename(source_pkg)"),
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
         dmg_source_path) = self.env['source_pkg'].partition(".dmg/")
        dmg_path += ".dmg"
        try:
            if dmg:
                # Mount dmg and copy path inside.
                mount_point = self.mount(dmg_path)
                source_pkg = os.path.join(mount_point, dmg_source_path)
            else:
                # Straight copy from file system.
                source_pkg = self.env["source_pkg"]


            # Prcess the path for globs
            matches = glob.glob(source_pkg)
            matched_source_path = matches[0]
            if len(matches) > 1:
                self.output("WARNING: Multiple paths match 'source_pkg' glob '%s':"
                    % source_pkg)
                for match in matches:
                    self.output("  - %s" % match)

            if [c for c in '*?[]!' if c in source_pkg]:
                self.output("Using path '%s' matched from globbed '%s'."
                    % (matched_source_path, source_pkg))

            # do the copy
            pkg_path = (self.env.get("pkg_path") or 
                os.path.join(self.env['RECIPE_CACHE_DIR'],
                             os.path.basename(source_pkg)))
            self.copy(matched_source_path, pkg_path, overwrite=True)
            self.env["pkg_path"] = pkg_path
            
        finally:
            if dmg:
                self.unmount(dmg_path)
    

if __name__ == '__main__':
    processor = Copier()
    processor.execute_shell()
