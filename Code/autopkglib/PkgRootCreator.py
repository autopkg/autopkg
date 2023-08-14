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
"""See docstring for PkgRootCreator class"""

import os.path
import shutil

from autopkglib import Processor, ProcessorError

__all__ = ["PkgRootCreator"]


# Download URLs in chunks of 256 kB.
CHUNK_SIZE = 256 * 1024


class PkgRootCreator(Processor):
    """Creates a package root and a directory structure.
    (Can also be used to create directory structures for other purposes.)"""

    description = __doc__
    input_variables = {
        "pkgroot": {
            "required": True,
            "description": "Path to where the package root will be created.",
        },
        "pkgdirs": {
            "required": True,
            "description": (
                "A dictionary of directories to be created "
                "inside the pkgroot, with their modes in octal form."
            ),
        },
    }
    output_variables = {}

    def main(self):
        # Delete pkgroot if it exists.
        try:
            if os.path.islink(self.env["pkgroot"]) or os.path.isfile(
                self.env["pkgroot"]
            ):
                os.unlink(self.env["pkgroot"])
            elif os.path.isdir(self.env["pkgroot"]):
                shutil.rmtree(self.env["pkgroot"])
        except OSError as err:
            raise ProcessorError(f"Can't remove {self.env['pkgroot']}: {err.strerror}") from err

        # Create pkgroot. autopkghelper sets it to root:admin 01775.
        try:
            os.makedirs(self.env["pkgroot"])
            self.output(f"Created {self.env['pkgroot']}")
        except OSError as err:
            raise ProcessorError(f"Can't create {self.env['pkgroot']}: {err.strerror}") from err

        # Create directories.
        absroot = os.path.abspath(self.env["pkgroot"])
        for directory, mode in sorted(self.env["pkgdirs"].items()):
            self.output(f"Creating {directory}", verbose_level=2)
            # Make sure we don't get an absolute path.
            if directory.startswith("/"):
                raise ProcessorError(f"{directory} in pkgroot is absolute.")
            dirpath = os.path.join(absroot, directory)

            # Make sure we're not trying to make a directory outside the
            # pkgroot.
            abspath = os.path.abspath(dirpath)
            if os.path.commonprefix((absroot, abspath)) != absroot:
                raise ProcessorError(f"{directory} is outside pkgroot")

            try:
                os.makedirs(dirpath)
                os.chmod(dirpath, int(mode, 8))
                self.output(f"Created {dirpath}")
            except OSError as err:
                raise ProcessorError(
                    f"Can't create {dirpath} with mode {mode}: {err.strerror}"
                ) from err


if __name__ == "__main__":
    PROCESSOR = PkgRootCreator()
    PROCESSOR.execute_shell()
