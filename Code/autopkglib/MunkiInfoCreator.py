#!/usr/bin/python
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
"""See docstring for MunkiInfoCreator class"""

import os.path
import plistlib
import shutil
import subprocess
import tempfile

from autopkglib import Processor, ProcessorError

__all__ = ["MunkiInfoCreator"]


class MunkiInfoCreator(Processor):
    """Creates a pkginfo file for a munki package."""

    description = __doc__
    input_variables = {
        "pkg_path": {
            "required": True,
            "description": "Path to a pkg or dmg in the munki repository.",
        },
        "version": {
            "required": False,
            "description": "Version to override makepkginfo.",
        },
        "name": {"required": False, "description": "Name to override makepkginfo."},
        "info_path": {"required": False, "description": "Path to the pkgsinfo file."},
    }
    output_variables = {"munki_info": {"description": "The pkginfo property list."}}

    def main(self):
        # Wrap in a try/finally so the temp_path is always removed.
        temp_path = None
        try:
            # Check munki version.
            if os.path.exists("/usr/local/munki/munkilib/version.plist"):
                # Assume 0.7.0 or higher.
                munkiopts = ("displayname", "description", "catalog")
            else:
                # Assume 0.6.0
                munkiopts = ("catalog",)

            # Copy pkg to a temporary local directory, as installer -query
            # (which is called by makepkginfo) doesn't work on network drives.
            if self.env["pkg_path"].endswith("pkg"):
                # Create temporary directory.
                temp_path = tempfile.mkdtemp(prefix="autopkg", dir="/private/tmp")

                # Copy the pkg there
                pkg_for_makepkginfo = os.path.join(
                    temp_path, os.path.basename(self.env["pkg_path"])
                )
                shutil.copyfile(self.env["pkg_path"], pkg_for_makepkginfo)
            else:
                pkg_for_makepkginfo = self.env["pkg_path"]

            # Generate arguments for makepkginfo.
            args = ["/usr/local/munki/makepkginfo"]
            for option in munkiopts:
                if option in self.env:
                    args.append("--%s=%s" % (option, self.env[option]))
            args.append(pkg_for_makepkginfo)

            # Call makepkginfo.
            try:
                proc = subprocess.Popen(
                    args, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                (stdout, stderr) = proc.communicate()
            except OSError as err:
                raise ProcessorError(
                    "makepkginfo execution failed with error code %d: %s"
                    % (err.errno, err.strerror)
                )
            if proc.returncode != 0:
                raise ProcessorError(
                    "creating pkginfo for %s failed: %s"
                    % (self.env["pkg_path"], stderr)
                )

        # makepkginfo cleanup.
        finally:
            if temp_path is not None:
                shutil.rmtree(temp_path)

        # Read output plist.
        output = plistlib.loads(stdout)

        # Set version and name.
        if "version" in self.env:
            output["version"] = self.env["version"]
        if "name" in self.env:
            output["name"] = self.env["name"]

        # Save info.
        self.env["munki_info"] = output
        if "info_path" in self.env:
            with open(self.env["info_path"], "wb") as f:
                plistlib.dump(output, f)


if __name__ == "__main__":
    PROCESSOR = MunkiInfoCreator()
    PROCESSOR.execute_shell()
