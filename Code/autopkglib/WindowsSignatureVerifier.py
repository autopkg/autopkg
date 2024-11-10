#!/usr/local/autopkg/python
#
# Copyright by Nick McSpadden, 2018
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
# 20190328 Nick Heim: Checks divided into status and certificate. JSON had errors in reading bigger cert trees at full size.
# 20201122 Nick Heim: Port to V2.2


"""See docstring for WindowsSignatureVerifier class"""

import json
import os.path
import re
import subprocess
import sys
from distutils.version import StrictVersion
from glob import glob

from autopkglib import ProcessorError, is_windows
from autopkglib.DmgMounter import DmgMounter

__all__ = ["WindowsSignatureVerifier"]


class WindowsSignatureVerifier(DmgMounter):
    """Verifies application installer package signature.

    Requires version 0.3.1."""

    input_variables = {
        "DISABLE_CODE_SIGNATURE_VERIFICATION": {
            "required": False,
            "description": (
                "Skip this Processor step altogether. Typically this "
                "would be invoked using AutoPkg's defaults or via '--key' "
                "CLI options at the time of the run, rather than being "
                "defined explicitly within a recipe."
            ),
        },
        "input_path": {
            "required": True,
            "description": ("File path to any codesigned file."),
        },
        "expected_subject": {
            "required": False,
            "description": (
                "The Subject of the Authenticode signature. Can be queried "
                "with:\n"
                "(Get-AuthenticodeSignature '<path>').SignerCertificate."
                "Subject"
            ),
        },
    }
    output_variables = {}

    description = __doc__

    def main(self):
        if not is_windows():
            self.output("Not on Windows, not running Windows Signature " "Verifier")
            return
        if self.env.get("DISABLE_CODE_SIGNATURE_VERIFICATION"):
            self.output("Code signature verification disabled for this recipe " "run.")
            return
        input_path = self.env["input_path"]
        powershell = "C:\\windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
        # Get cert status information from the file
        cmd = [
            powershell,
            " & {(Get-AuthenticodeSignature " + input_path + ").Status}",
        ]
        sigstat = subprocess.check_output(cmd).decode().rstrip()
        # Get cert information from the file
        if sigstat == "Valid":
            cmd = [
                powershell,
                " & {(Get-AuthenticodeSignature "
                + input_path
                + ").SignerCertificate|ConvertTo-Json}",
            ]
            # out = subprocess.check_output(cmd)
            out = subprocess.getoutput(cmd)
            # print >> sys.stdout, "Powershell out %s" % out
            # self.output("%s" % out,verbose_level=3)
            self.output(f"{out}", verbose_level=3)
            data = json.loads(out)
            if data["Subject"] != self.env["expected_subject"]:
                raise ProcessorError(
                    "Code signature mismatch! Expected %s but "
                    "received %s" % (self.env["expected_subject"], data["Subject"])
                )
        else:
            raise ProcessorError(
                "Code signature: not valid or not signed!"
                "Signature Status %s" % (sigstat)
            )


if __name__ == "__main__":
    PROCESSOR = WindowsSignatureVerifier()
    PROCESSOR.execute_shell()
