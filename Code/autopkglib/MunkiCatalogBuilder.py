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
"""See docstring for MunkiCatalogBuilder class"""

import subprocess

from autopkglib import Processor, ProcessorError

__all__ = ["MunkiCatalogBuilder"]


class MunkiCatalogBuilder(Processor):
    """Rebuilds Munki catalogs."""

    input_variables = {
        "MUNKI_REPO": {"required": True, "description": "Path to the Munki repo."},
        "munki_repo_changed": {
            "required": False,
            "description": (
                "If not defined or False, causes running " "makecatalogs to be skipped."
            ),
        },
    }
    output_variables = {}
    description = __doc__

    def main(self):
        # MunkiImporter or other processor must set
        # env["munki_repo_changed"] = True in order for makecatalogs
        # to run
        if not self.env.get("munki_repo_changed"):
            self.output("Skipping makecatalogs because repo is unchanged.")
            return

        # Generate arguments for makecatalogs.
        args = ["/usr/local/munki/makecatalogs", self.env["MUNKI_REPO"]]

        # Call makecatalogs.
        try:
            proc = subprocess.Popen(
                args, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            (_, err_out) = proc.communicate()
        except OSError as err:
            raise ProcessorError(
                f"makecatalog execution failed with error code {err.errno}: "
                f"{err.strerror}"
            )
        if proc.returncode != 0:
            raise ProcessorError(f"makecatalogs failed: {err_out}")
        self.output("Munki catalogs rebuilt!")


if __name__ == "__main__":
    PROCESSOR = MunkiCatalogBuilder()
    PROCESSOR.execute_shell()
