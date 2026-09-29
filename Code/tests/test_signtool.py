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
from unittest.mock import MagicMock, call, patch

from autopkglib.SignToolVerifier import (
    ProcessorError,
    SignToolVerifier,
    signtool_default_path,
)


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

    # --- signtool_default_path() tests ---

    def test_signtool_default_path_finds_x64_windows_kit(self):
        prog_files = r"C:\Program Files (x86)"
        module = sys.modules[SignToolVerifier.__module__]

        # Return True only when the candidate path contains the x64 arch token.
        def exists_side_effect(path):
            return r"\x64\signtool.exe" in path or "/x64/signtool.exe" in path

        with patch.dict("os.environ", {"ProgramFiles(x86)": prog_files}, clear=False):
            with patch.object(module.os.path, "exists", side_effect=exists_side_effect):
                result = signtool_default_path()

        self.assertIsNotNone(result)
        self.assertIn("x64", result)
        self.assertTrue(result.endswith("signtool.exe"))

    def test_signtool_default_path_finds_x86_windows_kit(self):
        prog_files = r"C:\Program Files (x86)"
        module = sys.modules[SignToolVerifier.__module__]

        # Return True only when the candidate path contains the x86 arch token
        # (but not x64, which is checked first).
        def exists_side_effect(path):
            if r"\x64\signtool.exe" in path or "/x64/signtool.exe" in path:
                return False
            return r"\x86\signtool.exe" in path or "/x86/signtool.exe" in path

        with patch.dict("os.environ", {"ProgramFiles(x86)": prog_files}, clear=False):
            with patch.object(module.os.path, "exists", side_effect=exists_side_effect):
                result = signtool_default_path()

        self.assertIsNotNone(result)
        self.assertIn("x86", result)
        self.assertTrue(result.endswith("signtool.exe"))

    def test_signtool_default_path_finds_github_actions_fallback(self):
        module = sys.modules[SignToolVerifier.__module__]
        github_path = (
            r"C:\Program Files (x86)\Windows Kits\10\App Certification Kit\signtool.exe"
        )

        def exists_side_effect(path):
            return path == github_path

        with patch.dict("os.environ", {}, clear=True):
            with patch.object(module.os.path, "exists", side_effect=exists_side_effect):
                result = signtool_default_path()

        self.assertEqual(result, github_path)

    def test_signtool_default_path_returns_none_when_not_found(self):
        module = sys.modules[SignToolVerifier.__module__]
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(module.os.path, "exists", return_value=False):
                result = signtool_default_path()

        self.assertIsNone(result)

    # --- codesign_verify() output / returncode tests ---

    def _make_proc(self, returncode, output):
        proc = MagicMock()
        proc.returncode = returncode
        proc.communicate.return_value = (output, None)
        return proc

    def test_codesign_verify_success_with_returncode_zero(self):
        processor = SignToolVerifier({})
        proc = self._make_proc(0, "Success")

        with patch("subprocess.Popen", return_value=proc):
            with patch.object(processor, "output") as mock_output:
                result = processor.codesign_verify(
                    r"C:\fake\signtool.exe", r"C:\fake\file.exe"
                )

        self.assertTrue(result)
        mock_output.assert_called_with("Success")

    def test_codesign_verify_failure_with_returncode_one(self):
        processor = SignToolVerifier({})
        proc = self._make_proc(1, "Error text")

        with patch("subprocess.Popen", return_value=proc):
            with patch.object(processor, "output") as mock_output:
                with self.assertRaisesRegex(
                    ProcessorError, "Authenticode verification failed"
                ):
                    processor.codesign_verify(
                        r"C:\fake\signtool.exe", r"C:\fake\file.exe"
                    )

        mock_output.assert_called_with("Error text")

    def test_codesign_verify_warning_with_returncode_two(self):
        processor = SignToolVerifier({})
        proc = self._make_proc(2, "Warning text")

        with patch("subprocess.Popen", return_value=proc):
            with patch.object(processor, "output") as mock_output:
                result = processor.codesign_verify(
                    r"C:\fake\signtool.exe", r"C:\fake\file.exe"
                )

        self.assertFalse(result)
        warning_calls = [
            c
            for c in mock_output.call_args_list
            if "WARNING: Verification had warnings" in str(c)
        ]
        self.assertTrue(warning_calls, "Expected WARNING output call not found")

    def test_codesign_verify_processes_multiline_output(self):
        processor = SignToolVerifier({})
        # Three consecutive line breaks collapse to one blank line.
        # After both replacements: "line1\nline2\n\nline3"
        raw_output = "line1\nline2\n\n\nline3"
        proc = self._make_proc(0, raw_output)

        with patch("subprocess.Popen", return_value=proc):
            with patch.object(processor, "output") as mock_output:
                processor.codesign_verify(r"C:\fake\signtool.exe", r"C:\fake\file.exe")

        # splitlines on "line1\nline2\n\nline3" -> ["line1", "line2", "", "line3"]
        expected_calls = [call("line1"), call("line2"), call(""), call("line3")]
        self.assertEqual(mock_output.call_args_list, expected_calls)

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
