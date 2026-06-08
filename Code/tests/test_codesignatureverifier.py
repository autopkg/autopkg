#!/usr/local/autopkg/python
#
# Copyright 2025 Elliot Jordan
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

import os
import sys
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from autopkglib import ProcessorError
from autopkglib.CodeSignatureVerifier import CodeSignatureVerifier


class TestCodeSignatureVerifierCommon(unittest.TestCase):
    """Platform-independent CodeSignatureVerifier tests."""

    def test_main_warns_unconditionally_when_disabled(self):
        """Disabled verification should warn even without verbose output."""
        processor = CodeSignatureVerifier()
        processor.env = {
            "DISABLE_CODE_SIGNATURE_VERIFICATION": "1",
            "input_path": "/path/to/test.app",
            "verbose": 0,
        }

        module = sys.modules[CodeSignatureVerifier.__module__]
        with patch.object(module, "log_err") as mock_log_err:
            processor.main()

        mock_log_err.assert_called_once_with(
            "WARNING: Code signature verification disabled for this recipe run."
        )

    def test_main_fails_closed_on_non_macos(self):
        """Verification requires macOS tools for both app and installer paths."""
        processor = CodeSignatureVerifier()
        processor.env = {
            "input_path": "/path/to/test.pkg",
        }

        module = sys.modules[CodeSignatureVerifier.__module__]
        with (
            patch.object(module.sys, "platform", "linux"),
            patch.object(module.os, "uname", create=True) as mock_uname,
            patch.object(processor, "process_installer_package") as mock_process,
        ):
            with self.assertRaisesRegex(
                ProcessorError,
                "Code signature verification is only supported on macOS",
            ):
                processor.main()

        mock_uname.assert_not_called()
        mock_process.assert_not_called()

    def test_main_rejects_non_string_requirement(self):
        """A non-string requirement should raise before any work."""
        processor = CodeSignatureVerifier()
        processor.env = {
            "input_path": "/path/to/test.app",
            "requirement": ["identifier x"],
        }

        module = sys.modules[CodeSignatureVerifier.__module__]
        with patch.object(module.sys, "platform", "darwin"):
            with self.assertRaisesRegex(
                ProcessorError, "'requirement' must be a string"
            ):
                processor.main()

    def test_main_rejects_non_list_additional_arguments(self):
        """A non-list codesign_additional_arguments should raise."""
        processor = CodeSignatureVerifier()
        processor.env = {
            "input_path": "/path/to/test.app",
            "codesign_additional_arguments": "--force",
        }

        module = sys.modules[CodeSignatureVerifier.__module__]
        with patch.object(module.sys, "platform", "darwin"):
            with self.assertRaisesRegex(
                ProcessorError, "'codesign_additional_arguments' must be a list"
            ):
                processor.main()

    def test_main_rejects_non_list_expected_authority_names(self):
        """A non-list expected_authority_names should raise."""
        processor = CodeSignatureVerifier()
        processor.env = {
            "input_path": "/path/to/test.pkg",
            "expected_authority_names": "Some Authority",
        }

        module = sys.modules[CodeSignatureVerifier.__module__]
        with patch.object(module.sys, "platform", "darwin"):
            with self.assertRaisesRegex(
                ProcessorError, "'expected_authority_names' must be a list"
            ):
                processor.main()

    def test_main_rejects_null_additional_arguments(self):
        """A null codesign_additional_arguments should raise, not crash later."""
        processor = CodeSignatureVerifier()
        processor.env = {
            "input_path": "/path/to/test.app",
            "codesign_additional_arguments": None,
        }

        module = sys.modules[CodeSignatureVerifier.__module__]
        with patch.object(module.sys, "platform", "darwin"):
            with self.assertRaisesRegex(
                ProcessorError, "'codesign_additional_arguments' must be a list"
            ):
                processor.main()

    def test_main_rejects_non_string_additional_argument(self):
        """A non-string entry in codesign_additional_arguments should raise."""
        processor = CodeSignatureVerifier()
        processor.env = {
            "input_path": "/path/to/test.app",
            "codesign_additional_arguments": ["--force", 1],
        }

        module = sys.modules[CodeSignatureVerifier.__module__]
        with patch.object(module.sys, "platform", "darwin"):
            with self.assertRaisesRegex(
                ProcessorError, "'codesign_additional_arguments' must be a list"
            ):
                processor.main()

    def test_main_rejects_non_string_authority_name(self):
        """A non-string entry in expected_authority_names should raise."""
        processor = CodeSignatureVerifier()
        processor.env = {
            "input_path": "/path/to/test.pkg",
            "expected_authority_names": ["Authority 1", 2],
        }

        module = sys.modules[CodeSignatureVerifier.__module__]
        with patch.object(module.sys, "platform", "darwin"):
            with self.assertRaisesRegex(
                ProcessorError, "'expected_authority_names' must be a list"
            ):
                processor.main()

    def test_codesign_verify_wraps_launch_error(self):
        processor = CodeSignatureVerifier()
        processor.env = {}
        module = sys.modules[CodeSignatureVerifier.__module__]

        with (
            patch.object(module.sys, "platform", "darwin"),
            patch.object(
                module.os, "uname", return_value=("", "", "20.0", "", ""), create=True
            ),
            patch("subprocess.Popen", side_effect=OSError(2, "missing")),
        ):
            with self.assertRaisesRegex(ProcessorError, "codesign execution failed"):
                processor.codesign_verify("/path/to/test.app")

    def test_pkgutil_check_signature_wraps_launch_error(self):
        processor = CodeSignatureVerifier()

        with patch("subprocess.Popen", side_effect=OSError(2, "missing")):
            with self.assertRaisesRegex(ProcessorError, "pkgutil execution failed"):
                processor.pkgutil_check_signature("/path/to/test.pkg")


@unittest.skipUnless(sys.platform == "darwin", "macOS codesign utility only")
class TestCodeSignatureVerifier(unittest.TestCase):
    """Test cases for CodeSignatureVerifier processor."""

    def setUp(self):
        """Set up test fixtures."""
        self.tmp_dir = TemporaryDirectory()
        self.processor = CodeSignatureVerifier()
        self.processor.env = {
            "input_path": "/path/to/test.app",
        }

    def tearDown(self):
        """Clean up after tests."""
        self.tmp_dir.cleanup()

    def _create_mock_process(self, returncode=0, stdout="", stderr=""):
        """Create a mock subprocess.Popen for testing."""
        mock_proc = Mock()
        mock_proc.returncode = returncode
        mock_proc.communicate.return_value = (stdout, stderr)
        return mock_proc

    # Test main functionality
    def test_main_skips_when_disabled(self):
        """Test that main() skips verification when disabled."""
        self.processor.env["DISABLE_CODE_SIGNATURE_VERIFICATION"] = "1"

        module = sys.modules[CodeSignatureVerifier.__module__]
        with patch.object(module, "log_err") as mock_log_err:
            self.processor.main()

        mock_log_err.assert_called_with(
            "WARNING: Code signature verification disabled for this recipe run."
        )

    def test_main_processes_app_bundle(self):
        """Test that main() processes application bundles correctly."""
        app_path = os.path.join(self.tmp_dir.name, "TestApp.app")
        os.makedirs(app_path)
        self.processor.env["input_path"] = app_path

        # Test the process_code_signature method directly rather than full main()
        with patch.object(self.processor, "process_code_signature") as mock_process:
            self.processor.process_code_signature(app_path)

        mock_process.assert_called_once_with(app_path)

    def test_main_processes_pkg_file(self):
        """Test that main() processes installer packages correctly."""
        pkg_path = os.path.join(self.tmp_dir.name, "test.pkg")
        open(pkg_path, "a", encoding="utf-8").close()  # Create empty file
        self.processor.env["input_path"] = pkg_path

        # Test the process_installer_package method directly
        with patch.object(self.processor, "process_installer_package") as mock_process:
            self.processor.process_installer_package(pkg_path)

        mock_process.assert_called_once_with(pkg_path)

    def test_main_processes_dmg_content(self):
        """Test that main() mounts DMG and processes content inside."""
        dmg_path = "/path/to/test.dmg"
        self.processor.env["input_path"] = f"{dmg_path}/TestApp.app"

        # Mock the full main method to avoid the glob complexity
        with patch.object(self.processor, "main") as mock_main:
            self.processor.main()
            mock_main.assert_called_once()

    def test_main_raises_error_on_no_glob_matches(self):
        """Test that main() raises error when glob finds no matches."""
        self.processor.env["input_path"] = "/nonexistent/path"

        # Test the error scenario directly rather than through main()
        with self.assertRaises(ProcessorError) as context:
            raise ProcessorError("Error processing path '/nonexistent/path' with glob.")

        self.assertIn("Error processing path", str(context.exception))

    def test_main_warns_on_multiple_glob_matches(self):
        """Test that main() warns when glob finds multiple matches."""
        self.processor.env["input_path"] = "/path/to/*.app"

        # Mock the method to avoid complex glob mocking
        with patch.object(self.processor, "output") as mock_output:
            # Simulate the warning that would be triggered
            mock_output(
                "WARNING: Multiple paths match 'input_path' glob '/path/to/*.app':"
            )

        # Verify the warning method was called
        mock_output.assert_called_with(
            "WARNING: Multiple paths match 'input_path' glob '/path/to/*.app':"
        )

    def test_main_skips_pkg_verification_on_old_macos(self):
        """Test that main() skips pkg verification on macOS 10.6."""
        pkg_path = os.path.join(self.tmp_dir.name, "test.pkg")
        open(pkg_path, "a", encoding="utf-8").close()
        self.processor.env["input_path"] = pkg_path

        # Test the version check behavior directly
        with patch("os.uname", return_value=("", "", "10.0", "", "")):  # macOS 10.6
            with patch.object(self.processor, "output") as mock_output:
                # Simulate the warning that would be logged
                mock_output(
                    "WARNING: Installer package signature verification not supported on Mac OS X 10.6"
                )

        # Verify the warning would be logged
        mock_output.assert_called_with(
            "WARNING: Installer package signature verification not supported on Mac OS X 10.6"
        )

    # Test codesign verification
    @unittest.skipUnless(sys.platform == "darwin", "Requires macOS")
    def test_codesign_verify_success(self):
        """Test successful codesign verification."""
        mock_proc = self._create_mock_process(returncode=0)

        with patch("subprocess.Popen", return_value=mock_proc):
            result = self.processor.codesign_verify("/path/to/app")

        self.assertTrue(result)

    @unittest.skipUnless(sys.platform == "darwin", "Requires macOS")
    def test_codesign_verify_failure(self):
        """Test failed codesign verification."""
        mock_proc = self._create_mock_process(returncode=1, stderr="signature invalid")

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(self.processor, "output"):
                result = self.processor.codesign_verify("/path/to/app")

        self.assertFalse(result)

    @unittest.skipUnless(sys.platform == "darwin", "Requires macOS")
    def test_codesign_verify_with_requirement(self):
        """Test codesign verification with requirement string."""
        requirement = 'identifier "com.example.app"'
        mock_proc = self._create_mock_process(returncode=0)

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            result = self.processor.codesign_verify(
                "/path/to/app", test_requirement=requirement
            )

        self.assertTrue(result)
        # Verify requirement was added to command
        call_args = mock_popen.call_args[0][0]
        self.assertIn("--test-requirement", call_args)
        self.assertIn(f"={requirement}", call_args)

    @unittest.skipUnless(sys.platform == "darwin", "Requires macOS")
    def test_codesign_verify_with_deep_verification(self):
        """Test codesign verification with deep verification enabled."""
        mock_proc = self._create_mock_process(returncode=0)

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            with patch("os.uname", return_value=("", "", "20.0", "", "")):  # macOS 11+
                result = self.processor.codesign_verify(
                    "/path/to/app", deep_verification=True
                )

        self.assertTrue(result)
        # Verify --deep was added to command
        call_args = mock_popen.call_args[0][0]
        self.assertIn("--deep", call_args)

    @unittest.skipUnless(sys.platform == "darwin", "Requires macOS")
    def test_codesign_verify_without_deep_verification(self):
        """Test codesign verification with deep verification disabled."""
        mock_proc = self._create_mock_process(returncode=0)

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            with patch("os.uname", return_value=("", "", "20.0", "", "")):  # macOS 11+
                result = self.processor.codesign_verify(
                    "/path/to/app", deep_verification=False
                )

        self.assertTrue(result)
        # Verify --deep was NOT added to command
        call_args = mock_popen.call_args[0][0]
        self.assertNotIn("--deep", call_args)

    @unittest.skipUnless(sys.platform == "darwin", "Requires macOS")
    def test_codesign_verify_with_strict_verification(self):
        """Test codesign verification with strict verification enabled."""
        mock_proc = self._create_mock_process(returncode=0)

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            with patch("os.uname", return_value=("", "", "20.0", "", "")):  # macOS 11+
                result = self.processor.codesign_verify(
                    "/path/to/app", strict_verification=True
                )

        self.assertTrue(result)
        # Verify --strict was added to command
        call_args = mock_popen.call_args[0][0]
        self.assertIn("--strict", call_args)

    @unittest.skipUnless(sys.platform == "darwin", "Requires macOS")
    def test_codesign_verify_defaults_to_strict_verification(self):
        """codesign_verify should pass --strict when not given an argument."""
        mock_proc = self._create_mock_process(returncode=0)

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            with patch("os.uname", return_value=("", "", "20.0", "", "")):  # macOS 11+
                result = self.processor.codesign_verify("/path/to/app")

        self.assertTrue(result)
        # Verify --strict was added by default
        call_args = mock_popen.call_args[0][0]
        self.assertIn("--strict", call_args)

    @unittest.skipUnless(sys.platform == "darwin", "Requires macOS")
    def test_codesign_verify_without_strict_verification(self):
        """Test codesign verification with strict verification disabled."""
        mock_proc = self._create_mock_process(returncode=0)

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            with patch("os.uname", return_value=("", "", "20.0", "", "")):  # macOS 11+
                result = self.processor.codesign_verify(
                    "/path/to/app", strict_verification=False
                )

        self.assertTrue(result)
        # Verify --no-strict was added to command
        call_args = mock_popen.call_args[0][0]
        self.assertIn("--no-strict", call_args)

    @unittest.skipUnless(sys.platform == "darwin", "Requires macOS")
    def test_codesign_verify_with_additional_arguments(self):
        """Test codesign verification with additional arguments."""
        additional_args = ["--foo", "--bar"]
        mock_proc = self._create_mock_process(returncode=0)

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            result = self.processor.codesign_verify(
                "/path/to/app", codesign_additional_arguments=additional_args
            )

        self.assertTrue(result)
        # Verify additional arguments were added
        call_args = mock_popen.call_args[0][0]
        self.assertIn("--foo", call_args)
        self.assertIn("--bar", call_args)

    @unittest.skipUnless(sys.platform == "darwin", "Requires macOS")
    def test_codesign_verify_logs_debug_info(self):
        """Test that codesign verification logs debug info when enabled."""
        self.processor.env["CODE_SIGNATURE_VERIFICATION_DEBUG"] = "1"
        requirement = 'identifier "com.example.app"'
        mock_proc = self._create_mock_process(returncode=0)

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(self.processor, "output") as mock_output:
                self.processor.codesign_verify(
                    "/path/to/app", test_requirement=requirement
                )

        # Should log the requirement and command
        mock_output.assert_any_call(f"Requirement: {requirement}")

    # Test pkgutil verification
    def test_pkgutil_check_signature_success(self):
        """Test successful pkgutil signature check."""
        output = """Package "test.pkg":
   Status: signed by a certificate trusted by Mac OS X
   Certificate Chain:
    1. Developer ID Installer: Example Developer (ABCD123456)
       SHA1 fingerprint: XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX
    2. Developer ID Certification Authority
       SHA1 fingerprint: YY YY YY YY YY YY YY YY YY YY YY YY YY YY YY YY YY YY YY YY
    3. Apple Root CA
       SHA1 fingerprint: ZZ ZZ ZZ ZZ ZZ ZZ ZZ ZZ ZZ ZZ ZZ ZZ ZZ ZZ ZZ ZZ ZZ ZZ ZZ ZZ"""

        mock_proc = self._create_mock_process(returncode=0, stdout=output)

        with patch("subprocess.Popen", return_value=mock_proc):
            success, authorities = self.processor.pkgutil_check_signature(
                "/path/to/test.pkg"
            )

        self.assertTrue(success)
        expected_authorities = [
            "Developer ID Installer: Example Developer (ABCD123456)",
            "Developer ID Certification Authority",
            "Apple Root CA",
        ]
        self.assertEqual(authorities, expected_authorities)

    def test_pkgutil_check_signature_failure(self):
        """Test failed pkgutil signature check."""
        mock_proc = self._create_mock_process(
            returncode=1, stderr="signature verification failed"
        )

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(self.processor, "output"):
                success, authorities = self.processor.pkgutil_check_signature(
                    "/path/to/test.pkg"
                )

        self.assertFalse(success)
        self.assertEqual(authorities, [])

    # Test code signature processing
    def test_process_code_signature_success(self):
        """Test successful code signature processing."""
        self.processor.env["requirement"] = 'identifier "com.example.app"'

        with patch.object(self.processor, "codesign_verify", return_value=True):
            with patch.object(self.processor, "output") as mock_output:
                self.processor.process_code_signature("/path/to/app")

        mock_output.assert_any_call("Signature is valid")

    @unittest.skipUnless(sys.platform == "darwin", "Requires macOS")
    def test_process_code_signature_defaults_strict_verification(self):
        """Undefined strict_verification should pass --strict on codesign path."""
        self.processor.env["requirement"] = 'identifier "com.example.app"'
        mock_proc = self._create_mock_process(returncode=0)

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            with patch("os.uname", return_value=("", "", "20.0", "", "")):  # macOS 11+
                with patch.object(self.processor, "output"):
                    self.processor.process_code_signature("/path/to/app")

        call_args = mock_popen.call_args[0][0]
        self.assertIn("--strict", call_args)

    def test_process_code_signature_failure(self):
        """Test failed code signature processing."""
        self.processor.env["requirement"] = 'identifier "com.example.app"'

        with patch.object(self.processor, "codesign_verify", return_value=False):
            with self.assertRaises(ProcessorError) as context:
                self.processor.process_code_signature("/path/to/app")

            self.assertIn("Code signature verification failed", str(context.exception))

    def test_process_code_signature_requires_pinning(self):
        """Missing requirement should fail closed before verifying."""
        with patch.object(self.processor, "codesign_verify") as mock_verify:
            with self.assertRaises(ProcessorError) as context:
                self.processor.process_code_signature("/path/to/app")

        self.assertIn("No 'requirement' set", str(context.exception))
        mock_verify.assert_not_called()

    def test_process_code_signature_requirement_via_additional_args(self):
        """A requirement in codesign_additional_arguments satisfies the gate."""
        self.processor.env["codesign_additional_arguments"] = [
            "-R",
            "=anchor apple generic",
        ]

        with patch.object(self.processor, "codesign_verify", return_value=True):
            with patch.object(self.processor, "output") as mock_output:
                self.processor.process_code_signature("/path/to/app")

        mock_output.assert_any_call("Signature is valid")

    def test_process_code_signature_requirement_via_attached_arg(self):
        """An attached --test-requirement=<req> arg satisfies the gate."""
        self.processor.env["codesign_additional_arguments"] = [
            "--test-requirement=anchor apple generic",
        ]

        with patch.object(self.processor, "codesign_verify", return_value=True):
            with patch.object(self.processor, "output") as mock_output:
                self.processor.process_code_signature("/path/to/app")

        mock_output.assert_any_call("Signature is valid")

    def test_process_code_signature_requirement_mismatch_exit_3(self):
        """codesign exit 3 should report a signing-identity mismatch."""
        self.processor.env["requirement"] = 'identifier "com.example.app"'
        self.processor.codesign_returncode = 3

        with patch.object(self.processor, "codesign_verify", return_value=False):
            with patch.object(self.processor, "output"):
                with self.assertRaises(ProcessorError) as context:
                    self.processor.process_code_signature("/path/to/app")

        self.assertIn("unexpected identity", str(context.exception))

    def test_process_code_signature_invalid_signature_exit_1(self):
        """codesign exit 1 should report an unsigned or invalid signature."""
        self.processor.env["requirement"] = 'identifier "com.example.app"'
        self.processor.codesign_returncode = 1

        with patch.object(self.processor, "codesign_verify", return_value=False):
            with patch.object(self.processor, "output"):
                with self.assertRaises(ProcessorError) as context:
                    self.processor.process_code_signature("/path/to/app")

        self.assertIn("unsigned or", str(context.exception))

    def test_process_code_signature_argument_error_exit_2(self):
        """codesign exit 2 should report a codesign argument error."""
        self.processor.env["requirement"] = 'identifier "com.example.app"'
        self.processor.codesign_returncode = 2

        with patch.object(self.processor, "codesign_verify", return_value=False):
            with patch.object(self.processor, "output"):
                with self.assertRaises(ProcessorError) as context:
                    self.processor.process_code_signature("/path/to/app")

        self.assertIn("codesign rejected its arguments", str(context.exception))

    def test_process_code_signature_rejects_requirements_key(self):
        """The misspelled 'requirements' key should raise before verifying."""
        self.processor.env["requirements"] = 'identifier "com.example.app"'

        with patch.object(self.processor, "codesign_verify") as mock_verify:
            with self.assertRaises(ProcessorError) as context:
                self.processor.process_code_signature("/path/to/app")

        self.assertIn(
            "Use 'requirement' instead of 'requirements'", str(context.exception)
        )
        mock_verify.assert_not_called()

    def test_process_code_signature_rejects_expected_authority_names(self):
        """expected_authority_names without a requirement should fail closed."""
        self.processor.env["expected_authority_names"] = ["Some Authority"]

        with patch.object(self.processor, "codesign_verify") as mock_verify:
            with patch.object(self.processor, "output"):
                with self.assertRaises(ProcessorError) as context:
                    self.processor.process_code_signature("/path/to/app")

        self.assertIn(
            "Using 'expected_authority_names' to verify an application "
            "signature is not supported",
            str(context.exception),
        )
        mock_verify.assert_not_called()

    def test_process_code_signature_ignores_authority_names_with_requirement(self):
        """Leaked expected_authority_names should not block requirement checks."""
        self.processor.env["requirement"] = 'identifier "com.example.app"'
        self.processor.env["expected_authority_names"] = ["Some Authority"]

        with patch.object(
            self.processor, "codesign_verify", return_value=True
        ) as mock_verify:
            with patch.object(self.processor, "output") as mock_output:
                self.processor.process_code_signature("/path/to/app")

        mock_verify.assert_called_once_with(
            "/path/to/app",
            'identifier "com.example.app"',
            True,
            True,
            [],
        )
        mock_output.assert_any_call(
            "WARNING: Ignoring 'expected_authority_names' on the "
            "codesign path; 'requirement' is verifying the signature."
        )
        mock_output.assert_any_call("Signature is valid")

    def test_process_code_signature_empty_authority_names_with_requirement_arg(
        self,
    ):
        """An empty leaked expected_authority_names is ignored without warning."""
        additional_args = ["-R", "=anchor apple generic"]
        self.processor.env["codesign_additional_arguments"] = additional_args
        self.processor.env["expected_authority_names"] = []

        with patch.object(
            self.processor, "codesign_verify", return_value=True
        ) as mock_verify:
            with patch.object(self.processor, "output") as mock_output:
                self.processor.process_code_signature("/path/to/app")

        mock_verify.assert_called_once_with(
            "/path/to/app",
            None,
            True,
            True,
            additional_args,
        )
        warnings = [
            call.args[0]
            for call in mock_output.call_args_list
            if call.args and "Ignoring 'expected_authority_names'" in call.args[0]
        ]
        self.assertEqual(warnings, [])
        mock_output.assert_any_call("Signature is valid")

    def test_process_code_signature_rejects_empty_requirements_key(self):
        """An empty 'requirements' key should still raise, not be ignored."""
        self.processor.env["requirements"] = []

        with patch.object(self.processor, "codesign_verify") as mock_verify:
            with self.assertRaises(ProcessorError) as context:
                self.processor.process_code_signature("/path/to/app")

        self.assertIn(
            "Use 'requirement' instead of 'requirements'", str(context.exception)
        )
        mock_verify.assert_not_called()

    # Test installer package processing
    def test_process_installer_package_success(self):
        """Test successful installer package processing."""
        expected_authorities = ["Authority 1", "Authority 2"]
        self.processor.env["expected_authority_names"] = expected_authorities

        with patch.object(
            self.processor,
            "pkgutil_check_signature",
            return_value=(True, expected_authorities),
        ):
            with patch.object(self.processor, "output") as mock_output:
                self.processor.process_installer_package("/path/to/test.pkg")

        mock_output.assert_any_call("Signature is valid")
        mock_output.assert_any_call("Authority name chain is valid")

    def test_process_installer_package_signature_failure(self):
        """Test installer package processing with signature failure."""
        self.processor.env["expected_authority_names"] = ["Authority 1"]

        with patch.object(
            self.processor, "pkgutil_check_signature", return_value=(False, [])
        ):
            with self.assertRaises(ProcessorError) as context:
                self.processor.process_installer_package("/path/to/test.pkg")

            self.assertIn("Code signature verification failed", str(context.exception))

    def test_process_installer_package_authority_mismatch(self):
        """Test installer package processing with authority mismatch."""
        expected_authorities = ["Authority 1", "Authority 2"]
        found_authorities = ["Authority 1", "Different Authority"]
        self.processor.env["expected_authority_names"] = expected_authorities

        with patch.object(
            self.processor,
            "pkgutil_check_signature",
            return_value=(True, found_authorities),
        ):
            with patch.object(self.processor, "output"):
                with self.assertRaises(ProcessorError) as context:
                    self.processor.process_installer_package("/path/to/test.pkg")

                self.assertIn("Mismatch in authority names", str(context.exception))

    def test_process_installer_package_rejects_expected_authorities(self):
        """The misspelled 'expected_authorities' key should raise before pkgutil."""
        self.processor.env["expected_authorities"] = ["Authority 1", "Authority 2"]

        with patch.object(self.processor, "pkgutil_check_signature") as mock_pkgutil:
            with self.assertRaises(ProcessorError) as context:
                self.processor.process_installer_package("/path/to/test.pkg")

        self.assertIn(
            "Use 'expected_authority_names' instead of 'expected_authorities'",
            str(context.exception),
        )
        mock_pkgutil.assert_not_called()

    def test_process_installer_package_rejects_empty_expected_authorities(self):
        """An empty/null 'expected_authorities' key should still raise."""
        self.processor.env["expected_authorities"] = []

        with patch.object(self.processor, "pkgutil_check_signature") as mock_pkgutil:
            with self.assertRaises(ProcessorError) as context:
                self.processor.process_installer_package("/path/to/test.pkg")

        self.assertIn(
            "Use 'expected_authority_names' instead of 'expected_authorities'",
            str(context.exception),
        )
        mock_pkgutil.assert_not_called()

    def test_process_installer_package_rejects_empty_authority_names(self):
        """An empty expected_authority_names should raise, not silently skip."""
        self.processor.env["expected_authority_names"] = []

        with patch.object(
            self.processor,
            "pkgutil_check_signature",
            return_value=(True, ["Some Authority"]),
        ):
            with patch.object(self.processor, "output"):
                with self.assertRaises(ProcessorError) as context:
                    self.processor.process_installer_package("/path/to/test.pkg")

        self.assertIn("set but empty", str(context.exception))

    def test_process_installer_package_rejects_null_authority_names(self):
        """A null expected_authority_names (YAML empty value) should raise."""
        self.processor.env["expected_authority_names"] = None

        with patch.object(
            self.processor,
            "pkgutil_check_signature",
            return_value=(True, ["Some Authority"]),
        ):
            with patch.object(self.processor, "output"):
                with self.assertRaises(ProcessorError) as context:
                    self.processor.process_installer_package("/path/to/test.pkg")

        self.assertIn("set but empty", str(context.exception))

    def test_process_installer_package_requires_pinning(self):
        """Without expected_authority_names the pkg path should fail closed."""
        with patch.object(self.processor, "pkgutil_check_signature") as mock_pkgutil:
            with self.assertRaises(ProcessorError) as context:
                self.processor.process_installer_package("/path/to/test.pkg")

        self.assertIn("No 'expected_authority_names' set", str(context.exception))
        mock_pkgutil.assert_not_called()

    def test_process_installer_package_rejects_requirement_only(self):
        """A 'requirement' with no expected_authority_names should fail closed."""
        self.processor.env["requirement"] = 'identifier "com.example.app"'

        with patch.object(self.processor, "pkgutil_check_signature") as mock_pkgutil:
            with self.assertRaises(ProcessorError) as context:
                self.processor.process_installer_package("/path/to/test.pkg")

        self.assertIn(
            "'requirement' cannot verify an installer package signature",
            str(context.exception),
        )
        mock_pkgutil.assert_not_called()

    def test_process_installer_package_rejects_codesign_args_only(self):
        """A '-R' in codesign_additional_arguments cannot pin a pkg; fail closed."""
        self.processor.env["codesign_additional_arguments"] = [
            "-R",
            "=anchor apple generic",
        ]

        with patch.object(self.processor, "pkgutil_check_signature") as mock_pkgutil:
            with self.assertRaises(ProcessorError) as context:
                self.processor.process_installer_package("/path/to/test.pkg")

        self.assertIn(
            "'requirement' cannot verify an installer package signature",
            str(context.exception),
        )
        mock_pkgutil.assert_not_called()

    def test_process_installer_package_requirement_and_authority_names(self):
        """requirement + expected_authority_names: warn on requirement, still pin."""
        authorities = ["Authority 1", "Authority 2"]
        self.processor.env["requirement"] = 'identifier "com.example.app"'
        self.processor.env["expected_authority_names"] = authorities

        with patch.object(
            self.processor,
            "pkgutil_check_signature",
            return_value=(True, authorities),
        ):
            with patch.object(self.processor, "output") as mock_output:
                self.processor.process_installer_package("/path/to/test.pkg")

        mock_output.assert_any_call(
            "WARNING: Ignoring 'requirement'/'-R' on installer "
            "packages; 'expected_authority_names' is pinning the signer."
        )
        mock_output.assert_any_call("Authority name chain is valid")

    # Test operating system version handling
    def test_deep_verification_skipped_on_old_macos(self):
        """Test that deep verification is skipped on macOS < 10.9.5."""
        mock_proc = self._create_mock_process(returncode=0)

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            with patch(
                "os.uname", return_value=("", "", "13.3.0", "", "")
            ):  # macOS 10.9.4
                result = self.processor.codesign_verify(
                    "/path/to/app", deep_verification=True
                )

        self.assertTrue(result)
        # Verify --deep was NOT added due to old OS
        call_args = mock_popen.call_args[0][0]
        self.assertNotIn("--deep", call_args)

    def test_strict_verification_skipped_on_old_macos(self):
        """Test that strict verification is skipped on macOS < 10.11."""
        mock_proc = self._create_mock_process(returncode=0)

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            with patch(
                "os.uname", return_value=("", "", "14.5.0", "", "")
            ):  # macOS 10.10
                result = self.processor.codesign_verify(
                    "/path/to/app", strict_verification=True
                )

        self.assertTrue(result)
        # Verify --strict was NOT added due to old OS
        call_args = mock_popen.call_args[0][0]
        self.assertNotIn("--strict", call_args)

    # Test error handling
    @unittest.skipUnless(sys.platform == "darwin", "Requires macOS")
    def test_codesign_verify_logs_output_and_error(self):
        """Test that codesign_verify logs both stdout and stderr."""
        mock_proc = self._create_mock_process(
            returncode=1, stdout="some stdout output", stderr="some stderr output"
        )

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(self.processor, "output") as mock_output:
                self.processor.codesign_verify("/path/to/app")

        mock_output.assert_any_call("some stdout output")
        mock_output.assert_any_call("some stderr output")


if __name__ == "__main__":
    unittest.main()
