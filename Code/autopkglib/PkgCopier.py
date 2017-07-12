#!/usr/bin/python
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
"""See docstring for PkgCopier class"""

import os.path
import glob

from autopkglib.Copier import Copier


__all__ = ["PkgCopier"]


class PkgCopier(Copier):
    """Copies source_pkg to pkg_path."""
    description = __doc__
    input_variables = {
        "source_pkg": {
            "required": True,
            "description": (
                "Path to a pkg to copy. Can point to a path inside "
                "a .dmg which will be mounted. This path may also contain "
                "basic globbing characters such as the wildcard '*', but only "
                "the first result will be returned."),
        },
        "pkg_path": {
            "required": False,
            "description": ("Path to destination. Defaults to "
                            "RECIPE_CACHE_DIR/os.path.basename(source_pkg)"),
        },
    }
    output_variables = {
        "pkg_path": {
            "description": "Path to copied pkg.",
        },
        "pkg_copier_summary_result": {
            "description": "Description of interesting results."
        }
    }

    def main(self):
        # clear any pre-exising summary result
        if 'pkg_copier_summary_result' in self.env:
            del self.env['pkg_copier_summary_result']

        # Check if we're trying to copy something inside a dmg.
        (dmg_path, dmg, dmg_source_path) = self.parsePathForDMG(
            self.env['source_pkg'])
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
                self.output(
                    "WARNING: Multiple paths match 'source_pkg' glob '%s':"
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
            self.env["pkg_copier_summary_result"] = {
                'summary_text': 'The following packages were copied:',
                'data': {
                    'pkg_path': pkg_path,
                }
            }

        finally:
            if dmg:
                self.unmount(dmg_path)


if __name__ == '__main__':
    PROCESSOR = Copier()
    PROCESSOR.execute_shell()
