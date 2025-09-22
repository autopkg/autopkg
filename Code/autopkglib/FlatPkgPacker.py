#!/usr/local/autopkg/python
#
# Copyright 2013 Jesse Peterson
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
"""See docstring for FlatPkgPacker class"""

import subprocess

from autopkglib import Processor, ProcessorError

__all__ = ["FlatPkgPacker"]


class FlatPkgPacker(Processor):
    """Flatten an expanded package using pkgutil.

    Requires AutoPkg version 0.2.4.
    """

    description = __doc__

    input_variables = {
        "source_flatpkg_dir": {
            "description": "Path to an extracted flat package",
            "required": True,
        },
        "destination_pkg": {
            "description": "Name of destination pkg to be flattened",
            "required": True,
        },
    }

    output_variables = {}

    def flatten(self, source_dir, dest_pkg):
        """Flattens a previously expanded flat package"""
        try:
            subprocess.check_call(
                ["/usr/sbin/pkgutil", "--flatten", source_dir, dest_pkg]
            )
        except subprocess.CalledProcessError as err:
            raise ProcessorError(f"{err} flattening {source_dir}")

    def main(self) -> None:
        source_dir = self.env.get("source_flatpkg_dir")
        dest_pkg = self.env.get("destination_pkg")

        self.flatten(source_dir, dest_pkg)

        self.output(f"Flattened {source_dir} to {dest_pkg}")


if __name__ == "__main__":
    PROCESSOR = FlatPkgPacker()
    PROCESSOR.execute_shell()
