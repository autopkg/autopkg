#!/usr/local/autopkg/python
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
"""See docstring for SignToolVerifier class"""

import os
import os.path
import subprocess
from typing import Any

from autopkglib import Processor, ProcessorError

__all__ = ["SignToolVerifier"]


def signtool_default_path() -> str | None:
    """Looks for signtool in a few well known paths. Deliberately naive."""
    for program_files_candidate, arch in (
        (os.environ.get("ProgramFiles(x86)"), "x64"),
        (os.environ.get("ProgramFiles(x86)"), "x86"),
        (os.environ.get("ProgramFiles"), "x64"),
        (os.environ.get("ProgramFiles"), "x86"),
    ):
        if program_files_candidate is None:
            continue
        candpath = os.path.abspath(
            os.path.join(
                program_files_candidate, r"Windows Kits\10\bin", arch, "signtool.exe"
            )
        )
        if os.path.exists(candpath):
            return candpath
    # fix for github hosted action runners:
    candpath = (
        r"C:\Program Files (x86)\Windows Kits\10\App Certification Kit\signtool.exe"
    )
    if os.path.exists(candpath):
        return candpath
    return None


class SignToolVerifier(Processor):
    """Verifies an authenticode signed installer using the Microsoft SDK
    signtool executable."""

    description = __doc__
    lifecycle = {"introduced": "2.3"}
    EXTENSIONS: list[str] = [".exe", ".msi"]

    # TODO: How much of this is needed to act as a drop-in replacement in an
    # override recipe??
    input_variables: dict[str, Any] = {
        "DISABLE_CODE_SIGNATURE_VERIFICATION": {
            "required": False,
            "description": ("Prevents this processor from running."),
        },
        "input_path": {
            "required": True,
            "description": (
                "File path to an `.msi` or `.exe` file for Authenticode verification",
            ),
        },
        "signtool_path": {
            "required": False,
            "description": (
                "The path to signtool.exe. This varies between versions of the "
                "Windows SDK, so you can explicitly set that here in an override."
            ),
            "default": signtool_default_path(),
        },
        "additional_arguments": {
            "required": False,
            "description": (
                "Array of additional argument strings to pass to signtool. "
                "Note that currently '/v' and '/pa' are always passed."
            ),
            "default": None,
        },
    }
    output_variables: dict[str, Any] = {}

    def codesign_verify(
        self,
        signtool_path: str,
        path: str,
        additional_arguments: list[str] | None = None,
    ) -> bool:
        """
        Runs 'signtool.exe /pa <path>'. Returns True if signtool exited with 0
        and False otherwise.
        """
        if not additional_arguments:
            additional_arguments = []

        # Call signtool with "/v" to produce information about the signer when run,
        # and "/pa" to use the "Default Authenticode" Verification Policy.
        process = [signtool_path, "verify", "/v", "/pa"] + additional_arguments

        # Makes the path absolute and normalizes it into standard Windows form.
        # E.g., /Program Files (x86)/Windows Kits/10/bin/x64/signtool.exe will be
        # converted to the appropriate C:\\... path after this.
        process.append(os.path.abspath(path))

        # Run signtool with stderr redirected to stdout to ensure that all output
        # is always captured from the tool.
        proc = subprocess.Popen(
            process,
            stdin=None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        output, _ = proc.communicate()

        for line in output.replace("\n\n", "\n").replace("\n\n\n", "\n\n").splitlines():
            self.output(line)

        if proc.returncode == 1:
            raise ProcessorError(
                "Authenticode verification failed. Note that all "
                "verification can be disabled by setting the variable "
                "DISABLE_CODE_SIGNATURE_VERIFICATION to a non-empty value."
            )
        elif proc.returncode == 2:
            self.output("WARNING: Verification had warnings. Check output above.")

        return proc.returncode == 0

    def main(self) -> None:
        if self.env.get("DISABLE_CODE_SIGNATURE_VERIFICATION"):
            self.output("Authenticode verification disabled for this recipe run.")
            return

        input_path = self.env["input_path"]
        signtool_path = self.env["signtool_path"]
        additional_arguments = self.env["additional_arguments"]

        self.codesign_verify(
            signtool_path,
            input_path,
            additional_arguments=additional_arguments,
        )


if __name__ == "__main__":
    PROCESSOR = SignToolVerifier()
    PROCESSOR.execute_shell()
