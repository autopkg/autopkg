#!/usr/local/autopkg/python
#
# Copyright 2020 Brian Smith
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

import sys
import unittest
from typing import Any
from unittest.mock import patch

from autopkglib.SignToolVerifier import ProcessorError, SignToolVerifier


class TestSignToolVerifier(unittest.TestCase):
    def test_main_warns_unconditionally_when_disabled(self):
        env: dict[str, Any] = {
            "DISABLE_CODE_SIGNATURE_VERIFICATION": "1",
            "input_path": r"C:\Fake\Path\To.exe",
            "verbose": 0,
        }
        processor = SignToolVerifier(env)

        module = sys.modules[SignToolVerifier.__module__]
        with patch.object(module, "log_err") as mock_log_err:
            processor.main()

        mock_log_err.assert_called_once_with(
            "WARNING: Authenticode verification disabled for this recipe run."
        )

    def test_main_rejects_missing_signtool_path(self):
        env: dict[str, Any] = {
            "input_path": r"C:\Fake\Path\To.exe",
            "signtool_path": None,
            "additional_arguments": None,
        }
        processor = SignToolVerifier(env)

        with self.assertRaisesRegex(ProcessorError, "No signtool_path configured"):
            processor.main()

    def test_codesign_verify_wraps_launch_error(self):
        processor = SignToolVerifier({})

        with patch("subprocess.Popen", side_effect=OSError(2, "missing")):
            with self.assertRaisesRegex(ProcessorError, "signtool execution failed"):
                processor.codesign_verify(
                    r"C:\Program Files\signtool.exe",
                    r"C:\Fake\Path\To.exe",
                )

    @unittest.skipUnless(sys.platform == "win32", "Requires Windows")
    def test_verify_ntdll(self):
        env: dict[str, str] = {"input_path": r"C:\Windows\System32\ntdll.dll"}
        processor = SignToolVerifier(env)
        self.assertIs(processor.process(), processor.env)

    @unittest.skipUnless(sys.platform == "win32", "Requires Windows")
    def test_verify_nopath(self):
        env: dict[str, Any] = {"input_path": r"C:\Fake\Path\To.dll", "verbose": 4}
        processor = SignToolVerifier(env)
        self.assertRaises(ProcessorError, processor.process)


if __name__ == "__main__":
    unittest.main()
