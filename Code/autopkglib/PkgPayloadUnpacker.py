#!/usr/local/autopkg/python
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
"""See docstring for PkgPayloadUnpacker class"""

import os
import shutil

from autopkglib import Processor, ProcessorError

__all__ = ["PkgPayloadUnpacker"]


class PkgPayloadUnpacker(Processor):
    """Unpacks a package payload."""

    input_variables = {
        "pkg_payload_path": {
            "required": True,
            "description": (
                "Path to a payload from an expanded flat package or "
                "Archive.pax.gz in a bundle package."
            ),
        },
        "destination_path": {"required": True, "description": "Destination directory."},
        "purge_destination": {
            "required": False,
            "description": (
                "Whether the contents of the destination directory will "
                "be removed before unpacking."
            ),
        },
    }
    output_variables = {}
    description = __doc__

    def unpack_pkg_payload(self):
        """Uses ditto to unpack a package payload into destination_path"""
        # Create the destination directory if needed.
        if not os.path.exists(self.env["destination_path"]):
            try:
                os.makedirs(self.env["destination_path"])
            except OSError as err:
                raise ProcessorError(
                    f"Can't create {self.env['destination_path']}: {err.strerror}"
                )
        elif self.env.get("purge_destination"):
            for entry in os.listdir(self.env["destination_path"]):
                path = os.path.join(self.env["destination_path"], entry)
                try:
                    if os.path.isdir(path) and not os.path.islink(path):
                        shutil.rmtree(path)
                    else:
                        os.unlink(path)
                except OSError as err:
                    raise ProcessorError(f"Can't remove {path}: {err.strerror}")

        cmd = [
            "/usr/bin/ditto",
            "-x",
            "-z",
            self.env["pkg_payload_path"],
            self.env["destination_path"],
        ]
        self.cmdexec(
            cmd,
            exception_text=f"extraction of {self.env['pkg_payload_path']} with ditto failed",
        )

        self.output(
            f"Unpacked {self.env['pkg_payload_path']} to {self.env['destination_path']}"
        )

    def main(self):
        self.unpack_pkg_payload()


if __name__ == "__main__":
    PROCESSOR = PkgPayloadUnpacker()
    PROCESSOR.execute_shell()
