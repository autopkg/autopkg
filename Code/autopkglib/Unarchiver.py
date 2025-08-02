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
"""See docstring for Unarchiver class"""

import os
import shutil
import subprocess
import tarfile
import zipfile
from typing import Union

from autopkglib import Processor, ProcessorError, is_mac

__all__ = ["Unarchiver"]

# Archive format types by file extension
EXTNS = {
    "zip": ["zip"],
    "tar_gzip": ["tar.gz", "tgz"],
    "tar_bzip2": ["tar.bz2", "tbz"],
    "tar": ["tar", "tar.xz"],
    "gzip": ["gzip"],
}

ExtractorType = Union[type[tarfile.TarFile], type[zipfile.ZipFile]]
Extractor = Union[tarfile.TarFile, zipfile.ZipFile]

# Native Python extractors for archive formats
NATIVE_EXTRACTORS: dict[str, ExtractorType] = {
    "tar_bzip2": tarfile.TarFile,
    "tar_gzip": tarfile.TarFile,
    "tar": tarfile.TarFile,
    "zip": zipfile.ZipFile,
    # gzip not supported for now -- 2020-07-22
}


def _default_use_python_native_extractor() -> bool:
    if is_mac():
        return False
    return True


class Unarchiver(Processor):
    """Archive decompressor for zip and common tar-compressed formats."""

    description = __doc__
    input_variables = {
        "archive_path": {
            "required": False,
            "description": "Path to an archive. Defaults to contents of the "
            "'pathname' variable, for example as is set by "
            "URLDownloader.",
        },
        "destination_path": {
            "required": False,
            "description": (
                "Directory where archive will be unpacked, created "
                "if necessary. Defaults to RECIPE_CACHE_DIR/NAME."
            ),
        },
        "purge_destination": {
            "required": False,
            "description": "Whether the contents of the destination directory "
            "will be removed before unpacking.",
        },
        "archive_format": {
            "required": False,
            "description": (
                "The archive format. Currently supported: 'zip', "
                "'tar_gzip', 'tar_bzip2', 'tar'. If omitted, the "
                "file extension is used to guess the format."
            ),
        },
        "USE_PYTHON_NATIVE_EXTRACTOR": {
            "required": False,
            "description": (
                "Controls whether or not Unarchiver extracts the archive with native "
                "Python code, or calls out to a platform specific utility. "
                "The default is determined on a platform specific basis. "
                "Currently, this means that on macOS platform utilities are used, "
                "and otherwise Python is used."
            ),
            "default": _default_use_python_native_extractor(),
        },
    }

    output_variables = {}

    def get_archive_format(self, archive_path):
        """Guess archive format based on filename extension"""
        for format_str, extns in list(EXTNS.items()):
            for extn in extns:
                if archive_path.endswith(extn):
                    return format_str
        # We found no known archive file extension if we got this far
        return None

    def _extract(self, fmt: str, archive_path: str, destination_path: str) -> None:
        if self.env["USE_PYTHON_NATIVE_EXTRACTOR"]:
            self._extract_native(fmt, archive_path, destination_path)
        else:
            self._extract_utility(fmt, archive_path, destination_path)

    def _extract_native(
        self, fmt: str, archive_path: str, destination_path: str
    ) -> None:
        archivefile_class: ExtractorType = NATIVE_EXTRACTORS[fmt]
        archive: Extractor = archivefile_class(archive_path, mode="r")
        try:
            archive.extractall(path=destination_path)
        except Exception as ex:
            raise ProcessorError(
                f"Unarchiving {archive_path} with <native extractor> failed: {ex}"
            )

    def _extract_utility(
        self, fmt: str, archive_path: str, destination_path: str
    ) -> None:
        """Extracts an archive using a platform specific utility."""
        if fmt == "zip":
            cmd = [
                "/usr/bin/ditto",
                "--noqtn",
                "-x",
                "-k",
                archive_path,
                destination_path,
            ]
        elif fmt == "gzip":
            cmd = ["/usr/bin/ditto", "--noqtn", "-x", archive_path, destination_path]
        elif fmt.startswith("tar"):
            cmd = ["/usr/bin/tar", "-x", "-f", archive_path, "-C", destination_path]
            if fmt.endswith("gzip"):
                cmd.append("-z")
            elif fmt.endswith("bzip2"):
                cmd.append("-j")

        # Call command.
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            (_, stderr) = proc.communicate()
        except OSError as err:
            raise ProcessorError(
                f"{os.path.basename(cmd[0])} execution failed with error code "
                f"{err.errno}: {err.strerror}"
            )
        if proc.returncode != 0:
            raise ProcessorError(
                f"Unarchiving {archive_path} with {os.path.basename(cmd[0])} failed: "
                f"{stderr}"
            )

    def main(self) -> None:
        """Unarchive a file"""
        # handle some defaults for archive_path and destination_path
        archive_path = self.env.get("archive_path", self.env.get("pathname"))
        if not archive_path:
            raise ProcessorError(
                "Expected an 'archive_path' input variable but none is set!"
            )
        destination_path = self.env.get(
            "destination_path",
            os.path.join(self.env["RECIPE_CACHE_DIR"], self.env["NAME"]),
        )

        # Create the directory if needed.
        if not os.path.exists(destination_path):
            try:
                os.makedirs(destination_path)
            except OSError as err:
                raise ProcessorError(f"Can't create {destination_path}: {err.strerror}")
        elif self.env.get("purge_destination"):
            for entry in os.listdir(destination_path):
                path = os.path.join(destination_path, entry)
                try:
                    if os.path.isdir(path) and not os.path.islink(path):
                        shutil.rmtree(path)
                    else:
                        os.unlink(path)
                except OSError as err:
                    raise ProcessorError(f"Can't remove {path}: {err.strerror}")

        fmt = self.env.get("archive_format")
        if fmt is None:
            fmt = self.get_archive_format(archive_path)
            if not fmt:
                raise ProcessorError(
                    "Can't guess archive format for filename "
                    f"{os.path.basename(archive_path)}"
                )
            self.output(
                f"Guessed archive format '{fmt}' from filename "
                f"{os.path.basename(archive_path)}"
            )
        elif fmt not in list(EXTNS.keys()):
            msg = ", ".join(list(EXTNS.keys()))
            raise ProcessorError(
                f"'{fmt}' is not valid for the 'archive_format' variable. "
                f"Must be one of {msg}."
            )

        self._extract(fmt, archive_path, destination_path)
        self.output(f"Unarchived {archive_path} to {destination_path}")

        # Clear archive_format in case there are subsequent Unarchiver processes
        if self.env.get("archive_format"):
            del self.env["archive_format"]


if __name__ == "__main__":
    PROCESSOR = Unarchiver()
    PROCESSOR.execute_shell()
