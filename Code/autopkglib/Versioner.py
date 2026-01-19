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
"""See docstring for Versioner class"""

import os.path
import posixpath
import zipfile
from collections.abc import Callable, Iterator

from autopkglib import FileOrPath, ProcessorError, VarDict
from autopkglib.DmgMounter import DmgMounter

# The version string to use when the version cannot be determined
UNKNOWN_VERSION = "UNKNOWN_VERSION"

__all__ = ["Versioner"]


def _zip_listdir(file: zipfile.ZipFile, directory: str) -> Iterator[zipfile.ZipInfo]:
    directory = directory.rstrip("/")

    def is_direct_child(info: zipfile.ZipInfo) -> bool:
        return posixpath.dirname(info.filename.rstrip("/")) == directory

    return filter(is_direct_child, file.infolist())


class Versioner(DmgMounter):
    """Returns version information from a plist"""

    description = __doc__

    input_variables = {
        "input_plist_path": {
            "required": True,
            "description": (
                "File path to a plist. Can point to a path inside a .dmg "
                "which will be mounted."
            ),
        },
        "plist_version_key": {
            "required": False,
            "default": "CFBundleShortVersionString",
            "description": (
                "Which plist key to use; defaults to CFBundleShortVersionString"
            ),
        },
        "skip_single_root_dir": {
            "required": False,
            "default": False,
            "description": (
                "If this flag is set, `input_plist_path` points inside a zip file, "
                "and there is a single directory inside the zip file at the root of "
                "the archive, then interpret the path in the archive as being relative "
                "to that directory. Example:"
                """
          input_plist_path=/tmp/some/archive.zip/path/to/version.plist
          archive.zip
            archive-abcdef/
              path/to/version.plist\n"""
                "        Will use `archive-abcdef/path/to/version.plist` as the final "
                "path. If there is more than one file or directory at the root, the "
                "Processor will fail."
            ),
        },
    }
    output_variables = {"version": {"description": "Version of the item."}}

    ZIP_EXTENSIONS = [".zip"]

    def _read_from_zip(
        self,
        path: str,
        skip_single_root_dir: bool,
        deserializer: Callable[[FileOrPath], VarDict],
        extensions: list[str],
    ) -> VarDict | None:
        """Parse a member from a zip and return `bytes`, or `None` if it does not exist.

        The `path` argument should be structured such that the path into the zip file
        follows the path to the zip file directly.

        Example:
            path/to/archive.zip/path/in/archive/to/version.plist
        If the flag `skip_single_root_dir` and there is more than one top-level
        directory inside the zip file, an exception will be raised.

        File extensions provided must be provided with a leading `.` i.e., `.zip`.
        All file extensions are considered case-insensitively.
        """
        # Normalize path to ensure consistent cross-platform behavior.
        path = os.path.normpath(path)
        archive_path: str | None = None
        inner_path: str | None = None
        for ext in extensions:
            ext_index: int = path.lower().find(f"{ext.lower()}{os.path.sep}")
            if ext_index == -1:
                continue
            archive_path = path[: ext_index + len(ext)]
            # Convert to POSIX path separators, as this is what zipfile uses.
            inner_path = path[ext_index + len(ext) + 1 :].replace("\\", "/")
            break
        if archive_path is None or inner_path is None:
            raise ProcessorError(
                f"Expected ZIP archive path, but '{path}' is not a ZIP path."
            )

        archive = zipfile.ZipFile(archive_path)
        root_names: list[zipfile.ZipInfo] = list(
            filter(zipfile.ZipInfo.is_dir, _zip_listdir(archive, ""))
        )
        if len(root_names) == 0:
            self.output(f"Zip archive '{archive_path}' is empty.")
            return None
        if not skip_single_root_dir:
            return deserializer(archive.open(inner_path))
        if skip_single_root_dir and len(root_names) > 1:
            raise ProcessorError(
                f"Zip archive '{archive_path}' has more than one directory at "
                f"root: {root_names} and skip_single_root_directory was set."
            )

        inner_path = posixpath.join(root_names[0].filename, inner_path)
        if inner_path not in archive.namelist():
            self.output(f"Zip archive '{archive_path}' does not contain '{inner_path}'")
            return None
        return deserializer(archive.open(inner_path))

    def _read_from_dmg(
        self,
        path: str,
        deserializer: Callable[[FileOrPath], VarDict],
    ) -> VarDict | None:
        """Parse a file from a DMG and return `bytes`, or `None` if no such file exists.

        The `path` argument should be structured such that the path into the disk image
        follows the path to the disk image directly.

        Example:
            path/to/disk.dmg/path/in/dmg/to/version.plist
        """
        # Check if we're trying to read something inside a dmg.
        dmg_path, dmg, dmg_source_path = self.parsePathForDMG(path)
        if not dmg:
            raise ProcessorError(f"Expected DMG path, but '{path}' is not a DMG path.")
        try:
            dmg_path = os.path.normpath(dmg_path)
            # Mount dmg and copy path inside.
            mount_point = self.mount(dmg_path)
            input_plist_path = os.path.normpath(
                os.path.join(mount_point, dmg_source_path)
            )
            if not os.path.exists(input_plist_path):
                return None
            try:
                return deserializer(input_plist_path)
            except Exception as err:
                raise ProcessorError(err)
        finally:
            self.unmount(dmg_path)
        return None

    def _read_auto_detect(
        self,
        path: str,
        skip_single_root_dir: bool,
        deserializer: Callable[[FileOrPath], VarDict],
    ) -> VarDict | None:
        """Use simple heuristics to read a file from a dmg, zip, or the filesystem.

        Returns `None` if the provided `path` could not be found. Exceptions are raised
        in the event that the file is corrupt or unaccessible.
        """
        is_dmg_input: list[bool] = [ext in path for ext in self.DMG_EXTENSIONS]
        is_zip_input: list[bool] = [ext in path for ext in self.ZIP_EXTENSIONS]
        if any(is_dmg_input):
            return self._read_from_dmg(path, deserializer)
        elif any(is_zip_input):
            return self._read_from_zip(
                path, skip_single_root_dir, deserializer, self.ZIP_EXTENSIONS
            )
        elif not os.path.exists(path):
            return None
        return deserializer(path)

    def main(self) -> None:
        """Return a version for file at input_plist_path"""
        input_plist_path: str = self.env["input_plist_path"]
        skip_single_root_dir: bool = self.env["skip_single_root_dir"]
        version_key: str = self.env["plist_version_key"]

        try:
            plist = self._read_auto_detect(
                input_plist_path, skip_single_root_dir, self.load_plist_from_file
            )
            if plist is None:
                raise ProcessorError(f"File '{input_plist_path}' was not found.")
            self.env["version"] = plist.get(version_key, UNKNOWN_VERSION)
            self.output(
                f"Found version {self.env['version']} in file {input_plist_path}"
            )
        except ProcessorError:
            raise
        except Exception as ex:
            raise ProcessorError(ex)


if __name__ == "__main__":
    PROCESSOR = Versioner()
    PROCESSOR.execute_shell()
