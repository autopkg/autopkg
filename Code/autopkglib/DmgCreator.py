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
"""See docstring for DmgCreator class"""

import os
import subprocess

from autopkglib import Processor, ProcessorError

__all__ = ["DmgCreator"]

DEFAULT_DMG_FORMAT = "UDZO"
DEFAULT_DMG_FILESYSTEM = "HFS+"
DEFAULT_ZLIB_LEVEL = 5


class DmgCreator(Processor):
    """Creates a disk image from a directory."""

    description = __doc__
    lifecycle = {"introduced": "0.1.0"}
    input_variables = {
        "dmg_root": {
            "required": True,
            "description": "Directory that will be copied to a disk image.",
        },
        "dmg_path": {"required": True, "description": "The dmg to be created."},
        "dmg_format": {
            "required": False,
            "description": (f"The dmg format. Defaults to {DEFAULT_DMG_FORMAT}."),
            "default": DEFAULT_DMG_FORMAT,
        },
        "dmg_filesystem": {
            "required": False,
            "description": (
                f"The dmg filesystem. Defaults to {DEFAULT_DMG_FILESYSTEM}."
            ),
            "default": DEFAULT_DMG_FILESYSTEM,
        },
        "dmg_zlib_level": {
            "required": False,
            "description": (
                "Compression level between '1' and '9' to use "
                f"when using UDZO. Defaults to '{DEFAULT_ZLIB_LEVEL}', a point "
                "beyond which very little space savings is "
                "gained."
            ),
            "default": DEFAULT_ZLIB_LEVEL,
        },
        "dmg_megabytes": {
            "required": False,
            "description": (
                "Value to set for the '-megabytes' option, useful "
                "as a workaround when hdiutil cannot accurately "
                "estimate the required size for the dmg before "
                "compression. Not normally required, and the "
                "option will not be used if this variable is not "
                "defined."
            ),
        },
    }
    output_variables = {}

    def main(self) -> None:
        # Remove existing dmg if it exists.
        if os.path.exists(self.env["dmg_path"]):
            os.unlink(self.env["dmg_path"])

        # Determine the format.
        # allow a subset of the formats supported by hdiutil, those
        # which aren't obsolete or deprecated
        valid_formats = [
            "UDRW",
            "UDRO",
            "UDCO",
            "UDZO",
            "UDBZ",
            "UFBI",
            "UDTO",
            "UDxx",
            "UDSP",
            "UDSB",
        ]

        dmg_format = self.env.get("dmg_format", DEFAULT_DMG_FORMAT)
        if dmg_format not in valid_formats:
            raise ProcessorError(
                f"dmg format '{dmg_format}' is invalid. Must be one of: "
                f"{', '.join(valid_formats)}."
            )

        zlib_level = int(self.env.get("dmg_zlib_level", DEFAULT_ZLIB_LEVEL))
        if zlib_level < 1 or zlib_level > 9:
            raise ProcessorError("dmg_zlib_level must be a value between 1 and 9.")

        # Allow any filesystem that hdiutil supports
        valid_filesystems = [
            "APFS",
            "Case-insensitive APFS",
            "Case-sensitive APFS",
            "Case-sensitive HFS+",
            "Case-sensitive Journaled HFS+",
            "ExFAT",
            "HFS+",
            "Journaled HFS+",
            "MS-DOS FAT12",
            "MS-DOS FAT16",
            "MS-DOS FAT32",
            "MS-DOS",
            "UDF",
        ]
        dmg_filesystem = self.env.get("dmg_filesystem", DEFAULT_DMG_FILESYSTEM)
        if dmg_filesystem not in valid_filesystems:
            raise ProcessorError(
                f"dmg filesystem '{dmg_filesystem}' is invalid. Must be one of: "
                f"{', '.join(valid_filesystems)}."
            )

        # Build a command for hdiutil.
        cmd = [
            "/usr/bin/hdiutil",
            "create",
            "-plist",
            "-fs",
            dmg_filesystem,
            "-format",
            dmg_format,
        ]
        if dmg_format == "UDZO":
            cmd.extend(["-imagekey", f"zlib-level={str(zlib_level)}"])
        if self.env.get("dmg_megabytes"):
            cmd.extend(["-megabytes", str(self.env["dmg_megabytes"])])
        cmd.extend(["-srcfolder", self.env["dmg_root"], self.env["dmg_path"]])

        # Call hdiutil.
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            (_, stderr) = proc.communicate()
        except OSError as err:
            raise ProcessorError(
                f"hdiutil execution failed with error code {err.errno}: {err.strerror}"
            )
        if proc.returncode != 0:
            raise ProcessorError(f"creation of {self.env['dmg_path']} failed: {stderr}")

        self.output(
            f"Created dmg from {self.env['dmg_root']} at {self.env['dmg_path']}"
        )


if __name__ == "__main__":
    PROCESSOR = DmgCreator()
    PROCESSOR.execute_shell()
