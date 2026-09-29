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

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

# Only load the module on Darwin, otherwise create dummy
if sys.platform == "darwin":
    # Load packager module directly from file to avoid mocking issues
    autopkgserver_path = Path(__file__).parent.parent / "autopkgserver" / "packager.py"
    spec = importlib.util.spec_from_file_location("packager", autopkgserver_path)
    packager_module = importlib.util.module_from_spec(spec)
    sys.modules["packager"] = packager_module
    spec.loader.exec_module(packager_module)
    Packager = packager_module.Packager
    PackagerError = packager_module.PackagerError
else:
    # Create dummy Packager for non-Darwin platforms
    Packager = MagicMock
    PackagerError = Exception


@unittest.skipUnless(sys.platform == "darwin", "Uses Unix grp module")
class TestPackager(unittest.TestCase):
    """Test class for Packager."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a minimal Packager instance for testing
        self.mock_log = MagicMock()
        self.mock_request = {}
        self.packager = Packager(
            log=self.mock_log,
            request=self.mock_request,
            name="test",
            uid=501,
            gid=20,
        )

    def test_random_string_contains_only_hex_chars(self):
        """Should only contain valid hex characters (0-9, a-f)."""
        result = self.packager.random_string(16)
        self.assertRegex(
            result,
            r"^[0-9a-f]+$",
            f"random_string returned invalid hex characters: {result}",
        )

    def test_random_string_returns_correct_length(self):
        """Should return string of requested length."""
        for length in [8, 16, 32]:
            result = self.packager.random_string(length)
            self.assertEqual(
                len(result),
                length,
                f"Expected length {length}, got {len(result)}: {result}",
            )

    @patch("packager.subprocess.run")
    def test_component_plist_read_wraps_ordinary_errors(self, mock_run):
        """Should still wrap ordinary plist read errors."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
        self.packager.tmproot = "/tmp/tmproot"
        self.packager.tmp_pkgroot = "/tmp/pkgroot"

        with (
            patch("builtins.open", mock_open()),
            patch("packager.plistlib.load", side_effect=ValueError),
            self.assertRaises(PackagerError),
        ):
            self.packager.make_component_property_list()

    @patch("packager.subprocess.run")
    def test_component_plist_read_does_not_wrap_keyboard_interrupt(self, mock_run):
        """Should let process termination exceptions propagate."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
        self.packager.tmproot = "/tmp/tmproot"
        self.packager.tmp_pkgroot = "/tmp/pkgroot"

        with (
            patch("builtins.open", mock_open()),
            patch("packager.plistlib.load", side_effect=KeyboardInterrupt),
            self.assertRaises(KeyboardInterrupt),
        ):
            self.packager.make_component_property_list()

    @patch("packager.subprocess.run")
    def test_component_plist_write_does_not_wrap_keyboard_interrupt(self, mock_run):
        """Should let process termination exceptions propagate."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
        self.packager.tmproot = "/tmp/tmproot"
        self.packager.tmp_pkgroot = "/tmp/pkgroot"

        with (
            patch("builtins.open", mock_open()),
            patch("packager.plistlib.load", return_value=[{}]),
            patch("packager.plistlib.dump", side_effect=KeyboardInterrupt),
            self.assertRaises(KeyboardInterrupt),
        ):
            self.packager.make_component_property_list()

    def test_copy_pkgroot_raises_on_failed_ditto(self):
        self.packager.request = {"pkgroot": "/source/pkgroot"}
        ditto_error = subprocess.CalledProcessError(
            1, ["/usr/bin/ditto"], stderr="copy failed\n"
        )

        with (
            patch("packager.tempfile.mkdtemp", return_value="/tmp/tmproot"),
            patch("packager.os.mkdir"),
            patch("packager.os.chmod"),
            patch("packager.os.chown"),
            patch("packager.subprocess.run", side_effect=ditto_error) as mock_run,
            self.assertRaisesRegex(PackagerError, "copy failed"),
        ):
            self.packager.copy_pkgroot()

        self.assertTrue(mock_run.call_args.kwargs["check"])

    def test_copy_pkgroot_preserves_ditto_launch_errors(self):
        self.packager.request = {"pkgroot": "/source/pkgroot"}

        with (
            patch("packager.tempfile.mkdtemp", return_value="/tmp/tmproot"),
            patch("packager.os.mkdir"),
            patch("packager.os.chmod"),
            patch("packager.os.chown"),
            patch(
                "packager.subprocess.run",
                side_effect=OSError(2, "No such file or directory"),
            ),
            self.assertRaisesRegex(PackagerError, "error code 2"),
        ):
            self.packager.copy_pkgroot()


@unittest.skipUnless(sys.platform == "darwin", "Uses Unix grp module")
class TestPackagerCreatePkgCommand(unittest.TestCase):
    """Test that create_pkg builds the correct pkgbuild command."""

    def _make_packager(self, request):
        mock_log = MagicMock()
        pkgr = Packager(log=mock_log, request=request, name="test", uid=501, gid=20)
        pkgr.tmp_pkgroot = "/tmp/pkgroot"
        pkgr.component_plist = "/tmp/component.plist"
        pkgr.tmproot = "/tmp/tmproot"
        return pkgr

    @patch("packager.os.chown")
    @patch("packager.os.rename")
    @patch("packager.subprocess.run")
    def test_pkgbuild_args_appear_before_output_path(
        self, mock_run, mock_rename, mock_chown
    ):
        """Extra pkgbuild_args should appear after standard flags but before the output path."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        request = {
            "pkgtype": "flat",
            "pkgname": "Test",
            "pkgdir": "/tmp/output",
            "id": "com.example.test",
            "version": "1.0",
            "infofile": "",
            "scripts": "",
            "pkgbuild_args": ["--filter", "\\.DS_Store$", "--large-payload"],
        }
        pkgr = self._make_packager(request)
        pkgr.create_pkg()

        cmd = mock_run.call_args[0][0]
        # Extra args should be present
        self.assertIn("--filter", cmd)
        self.assertIn("\\.DS_Store$", cmd)
        self.assertIn("--large-payload", cmd)
        # Output path is always last
        self.assertTrue(cmd[-1].endswith(".pkg"))
        # Extra args come before output path
        filter_idx = cmd.index("--filter")
        self.assertLess(filter_idx, len(cmd) - 1)

    @patch("packager.os.chown")
    @patch("packager.os.rename")
    @patch("packager.subprocess.run")
    def test_no_pkgbuild_args_omits_extra_flags(
        self, mock_run, mock_rename, mock_chown
    ):
        """Without pkgbuild_args, command should have no extra flags."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        request = {
            "pkgtype": "flat",
            "pkgname": "Test",
            "pkgdir": "/tmp/output",
            "id": "com.example.test",
            "version": "1.0",
            "infofile": "",
            "scripts": "",
        }
        pkgr = self._make_packager(request)
        pkgr.create_pkg()

        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0], "/usr/bin/pkgbuild")
        self.assertTrue(cmd[-1].endswith(".pkg"))
        self.assertNotIn("--filter", cmd)
        self.assertNotIn("--large-payload", cmd)


if __name__ == "__main__":
    unittest.main()
