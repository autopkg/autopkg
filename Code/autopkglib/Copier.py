#!/usr/local/autopkg/python
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
"""See docstring for Copier class"""

import glob
import os.path
import shutil

from autopkglib import ProcessorError
from autopkglib.DmgMounter import DmgMounter

__all__ = ["Copier"]


class Copier(DmgMounter):
    """Copies source_path to destination_path."""

    description = __doc__
    lifecycle = {"introduced": "0.1.0"}
    input_variables = {
        "source_path": {
            "required": True,
            "description": (
                "Path to a file or directory to copy. "
                "Can point to a path inside a .dmg which will be mounted. "
                "This path may also contain globbing patterns such as the "
                "wildcard '*', or '**' that matches optional subdirectories "
                "but only the first result will be returned."
            ),
        },
        "destination_path": {"required": True, "description": "Path to destination."},
        "overwrite": {
            "required": False,
            "description": (
                "Whether the destination will be overwritten if necessary. "
                "Uses a boolean value."
            ),
        },
    }
    output_variables = {}

    def copy(self, source_item, dest_item, overwrite=False):
        """Copies source_item to dest_item, overwriting if allowed"""
        # Remove destination if needed.
        if os.path.exists(dest_item) and overwrite:
            try:
                if os.path.isdir(dest_item) and not os.path.islink(dest_item):
                    shutil.rmtree(dest_item)
                else:
                    os.unlink(dest_item)
            except OSError as err:
                raise ProcessorError(f"Can't remove {dest_item}: {err.strerror}")

        # Copy file or directory.
        try:
            if os.path.isdir(source_item):
                shutil.copytree(source_item, dest_item, symlinks=True)
            elif not os.path.isdir(dest_item):
                shutil.copyfile(source_item, dest_item)
            else:
                shutil.copy(source_item, dest_item)
            self.output(f"Copied {source_item} to {dest_item}")
        except BaseException as err:
            raise ProcessorError(f"Can't copy {source_item} to {dest_item}: {err}")

    def main(self) -> None:
        source_path = self.env["source_path"]
        # Check if we're trying to copy something inside a dmg.
        dmg_path, dmg, dmg_source_path = self.parsePathForDMG(source_path)
        self.output(
            f"Parsed dmg results: dmg_path: {dmg_path}, dmg: {dmg}, "
            f"dmg_source_path: {dmg_source_path}",
            verbose_level=2,
        )
        try:
            if dmg:
                # Mount dmg and copy path inside.
                mount_point = self.mount(dmg_path)
                source_path = os.path.join(mount_point, dmg_source_path)
            # process path with glob.glob
            matches = glob.glob(source_path, recursive=True)
            if len(matches) == 0:
                raise ProcessorError(
                    f"Error processing path '{source_path}' with glob. "
                )
            matched_source_path = matches[0]
            if len(matches) > 1:
                self.output(
                    f"WARNING: Multiple paths match 'source_path' glob '{source_path}':"
                )
                for match in matches:
                    self.output(f"  - {match}")

            if [c for c in "*?[]!" if c in source_path]:
                self.output(
                    f"Using path '{matched_source_path}' matched from "
                    f"globbed '{source_path}'."
                )

            # do the copy
            self.copy(
                matched_source_path,
                self.env["destination_path"],
                overwrite=self.env.get("overwrite"),
            )
        finally:
            if dmg:
                self.unmount(dmg_path)


if __name__ == "__main__":
    PROCESSOR = Copier()
    PROCESSOR.execute_shell()
