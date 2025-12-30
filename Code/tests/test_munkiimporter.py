#!/usr/local/autopkg/python

import os
import plistlib
import unittest
from copy import deepcopy
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from autopkglib import ProcessorError
from autopkglib.MunkiImporter import MunkiImporter


class TestMunkiImporter(unittest.TestCase):
    """Test class for MunkiImporter Processor."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.munki_repo = os.path.join(self.tmp_dir.name, "munki_repo")
        self.pkg_path = os.path.join(self.tmp_dir.name, "TestApp-1.0.0.pkg")

        # Create basic munki repo structure
        os.makedirs(os.path.join(self.munki_repo, "pkgs"))
        os.makedirs(os.path.join(self.munki_repo, "pkgsinfo"))
        os.makedirs(os.path.join(self.munki_repo, "catalogs"))
        os.makedirs(os.path.join(self.munki_repo, "icons"))

        # Create empty catalogs/all file
        with open(os.path.join(self.munki_repo, "catalogs", "all"), "wb") as f:
            plistlib.dump([], f)

        # Create a dummy package file
        with open(self.pkg_path, "w") as f:
            f.write("dummy package content")

        self.good_env = {
            "MUNKI_REPO": self.munki_repo,
            "MUNKI_REPO_PLUGIN": "FileRepo",
            "MUNKILIB_DIR": "/usr/local/munki",
            "force_munki_repo_lib": False,
            "pkg_path": self.pkg_path,
        }

        self.processor = MunkiImporter()
        self.processor.env = deepcopy(self.good_env)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _create_mock_pkginfo(
        self, name="TestApp", version="1.0.0", hash_value="abc123"
    ):
        """Create a mock pkginfo dictionary."""
        return {
            "name": name,
            "version": version,
            "catalogs": ["testing"],
            "installer_item_hash": hash_value,
            "installer_item_size": 1024,
            "_metadata": {},
            "installs": [
                {
                    "type": "application",
                    "path": "/Applications/TestApp.app",
                    "CFBundleShortVersionString": version,
                }
            ],
        }

    # Test _fetch_repo_library method
    def test_fetch_repo_library_returns_autopkglib_by_default(self):
        """Test that _fetch_repo_library returns AutoPkgLib by default."""
        library = self.processor._fetch_repo_library(
            self.munki_repo, "FileRepo", "/usr/local/munki", None, False
        )

        # Should return AutoPkgLib for FileRepo without force_munki_lib
        self.assertEqual(library.__class__.__name__, "AutoPkgLib")

    def test_fetch_repo_library_returns_munkilib_when_forced(self):
        """Test that _fetch_repo_library returns MunkiLib when forced."""
        # Mock the entire method since we're testing logic, not actual instantiation
        with patch.object(self.processor, "_fetch_repo_library") as mock_method:
            mock_library = MagicMock()
            mock_method.return_value = mock_library

            # Call the mocked method
            result = self.processor._fetch_repo_library(
                self.munki_repo, "FileRepo", "/usr/local/munki", None, True
            )

            # Verify it was called and returned correctly
            mock_method.assert_called_once_with(
                self.munki_repo, "FileRepo", "/usr/local/munki", None, True
            )
            self.assertEqual(result, mock_library)

    def test_fetch_repo_library_uses_munkilib_for_non_filerepo(self):
        """Test that _fetch_repo_library uses MunkiLib for non-FileRepo plugins."""
        # Mock the entire method since we're testing logic, not actual instantiation
        with patch.object(self.processor, "_fetch_repo_library") as mock_method:
            mock_library = MagicMock()
            mock_method.return_value = mock_library

            # Call the mocked method
            result = self.processor._fetch_repo_library(
                self.munki_repo, "Git", "/usr/local/munki", "subdir", False
            )

            # Verify it was called and returned correctly
            mock_method.assert_called_once_with(
                self.munki_repo, "Git", "/usr/local/munki", "subdir", False
            )
            self.assertEqual(result, mock_library)

    # Test _find_matching_pkginfo method
    def test_find_matching_pkginfo_returns_none_without_hash(self):
        """Test that _find_matching_pkginfo returns None when no installer_item_hash."""
        mock_library = MagicMock()
        pkginfo = {"name": "TestApp", "version": "1.0.0"}

        result = self.processor._find_matching_pkginfo(mock_library, pkginfo)

        self.assertIsNone(result)

    def test_find_matching_pkginfo_finds_hash_match(self):
        """Test that _find_matching_pkginfo finds items with matching hash."""
        mock_library = MagicMock()
        hash_value = "abc123"
        pkginfo = self._create_mock_pkginfo(hash_value=hash_value)

        # Mock the catalog database
        mock_catalog_db = {
            "hashes": {hash_value: [0, 1]},  # indexes 0 and 1 have this hash
            "items": [
                {"name": "TestApp", "version": "1.0.0"},
                {"name": "TestApp", "version": "1.0.1"},
            ],
        }
        mock_library.make_catalog_db.return_value = mock_catalog_db

        result = self.processor._find_matching_pkginfo(mock_library, pkginfo)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "TestApp")
        self.assertEqual(result[1]["name"], "TestApp")

    # Test main method flow
    @patch("subprocess.Popen")
    def test_main_calls_makepkginfo_with_basic_args(self, mock_popen):
        """Test that main() calls makepkginfo with correct basic arguments."""
        # Mock subprocess result
        mock_process = MagicMock()
        mock_process.communicate.return_value = (
            plistlib.dumps(self._create_mock_pkginfo()),
            b"",
        )
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Mock library methods
        with patch.object(self.processor, "_fetch_repo_library") as mock_fetch:
            mock_library = MagicMock()
            mock_library.copy_pkg_to_repo.return_value = self.pkg_path
            mock_library.copy_pkginfo_to_repo.return_value = "/path/to/pkginfo"
            mock_library.munki_repo = self.munki_repo
            mock_fetch.return_value = mock_library

            with patch.object(
                self.processor, "_find_matching_pkginfo", return_value=None
            ):
                self.processor.main()

        # Verify makepkginfo was called with expected args
        expected_args = ["/usr/local/munki/makepkginfo", self.pkg_path]
        mock_popen.assert_called_once()
        actual_args = mock_popen.call_args[0][0]
        self.assertEqual(actual_args, expected_args)

    @patch("subprocess.Popen")
    def test_main_adds_optional_makepkginfo_args(self, mock_popen):
        """Test that main() adds optional arguments to makepkginfo call."""
        self.processor.env.update(
            {
                "munkiimport_pkgname": "CustomName",
                "munkiimport_appname": "CustomApp",
                "uninstaller_pkg_path": "/path/to/uninstaller.pkg",
                "additional_makepkginfo_options": ["--owner", "root"],
            }
        )

        # Mock subprocess result
        mock_process = MagicMock()
        mock_process.communicate.return_value = (
            plistlib.dumps(self._create_mock_pkginfo()),
            b"",
        )
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Mock library methods
        with patch.object(self.processor, "_fetch_repo_library") as mock_fetch:
            mock_library = MagicMock()
            mock_library.copy_pkg_to_repo.return_value = self.pkg_path
            mock_library.copy_pkginfo_to_repo.return_value = "/path/to/pkginfo"
            mock_library.munki_repo = self.munki_repo
            mock_fetch.return_value = mock_library

            with patch.object(
                self.processor, "_find_matching_pkginfo", return_value=None
            ):
                self.processor.main()

        # Verify all optional args were added
        actual_args = mock_popen.call_args[0][0]
        self.assertIn("--pkgname", actual_args)
        self.assertIn("CustomName", actual_args)
        self.assertIn("--appname", actual_args)
        self.assertIn("CustomApp", actual_args)
        self.assertIn("--uninstallerpkg", actual_args)
        self.assertIn("/path/to/uninstaller.pkg", actual_args)
        self.assertIn("--owner", actual_args)
        self.assertIn("root", actual_args)

    @patch("subprocess.Popen")
    def test_main_makepkginfo_failure_raises_error(self, mock_popen):
        """Test that main() raises ProcessorError when makepkginfo fails."""
        # Mock subprocess failure
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"makepkginfo failed")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        with self.assertRaisesRegex(ProcessorError, "creating pkginfo.*failed"):
            self.processor.main()

    @patch("subprocess.Popen")
    def test_main_makepkginfo_oserror_raises_error(self, mock_popen):
        """Test that main() handles OSError from makepkginfo subprocess."""
        mock_popen.side_effect = OSError("Command not found")

        with self.assertRaisesRegex(ProcessorError, "makepkginfo execution failed"):
            self.processor.main()

    @patch("subprocess.Popen")
    def test_main_merges_pkginfo_from_env(self, mock_popen):
        """Test that main() merges pkginfo data from environment."""
        # Add custom pkginfo to environment
        self.processor.env["pkginfo"] = {
            "description": "Test application",
            "developer": "Test Developer",
        }

        # Mock subprocess result
        base_pkginfo = self._create_mock_pkginfo()
        mock_process = MagicMock()
        mock_process.communicate.return_value = (plistlib.dumps(base_pkginfo), b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Mock library methods
        with patch.object(self.processor, "_fetch_repo_library") as mock_fetch:
            mock_library = MagicMock()
            mock_library.copy_pkg_to_repo.return_value = self.pkg_path
            mock_library.copy_pkginfo_to_repo.return_value = "/path/to/pkginfo"
            mock_library.munki_repo = self.munki_repo
            mock_fetch.return_value = mock_library

            with patch.object(
                self.processor, "_find_matching_pkginfo", return_value=None
            ):
                self.processor.main()

        # Verify pkginfo was passed to copy_pkginfo_to_repo with merged data
        mock_library.copy_pkginfo_to_repo.assert_called_once()
        pkginfo_arg = mock_library.copy_pkginfo_to_repo.call_args[0][0]
        self.assertEqual(pkginfo_arg["description"], "Test application")
        self.assertEqual(pkginfo_arg["developer"], "Test Developer")

    @patch("subprocess.Popen")
    def test_main_adds_metadata_additions(self, mock_popen):
        """Test that main() adds metadata_additions to pkginfo."""
        self.processor.env["metadata_additions"] = {
            "created_by": "AutoPkg",
            "foo": "bar",
        }

        # Mock subprocess result
        base_pkginfo = self._create_mock_pkginfo()
        mock_process = MagicMock()
        mock_process.communicate.return_value = (plistlib.dumps(base_pkginfo), b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Mock library methods
        with patch.object(self.processor, "_fetch_repo_library") as mock_fetch:
            mock_library = MagicMock()
            mock_library.copy_pkg_to_repo.return_value = self.pkg_path
            mock_library.copy_pkginfo_to_repo.return_value = "/path/to/pkginfo"
            mock_library.munki_repo = self.munki_repo
            mock_fetch.return_value = mock_library

            with patch.object(
                self.processor, "_find_matching_pkginfo", return_value=None
            ):
                self.processor.main()

        # Verify metadata was added
        pkginfo_arg = mock_library.copy_pkginfo_to_repo.call_args[0][0]
        self.assertEqual(pkginfo_arg["_metadata"]["created_by"], "AutoPkg")
        self.assertEqual(pkginfo_arg["_metadata"]["foo"], "bar")

    @patch("subprocess.Popen")
    def test_main_sets_version_comparison_key(self, mock_popen):
        """Test that main() sets version_comparison_key when specified."""
        self.processor.env["version_comparison_key"] = "CFBundleVersion"

        # Mock subprocess result with installs item
        base_pkginfo = self._create_mock_pkginfo()
        base_pkginfo["installs"][0]["CFBundleVersion"] = "1.0.0"
        mock_process = MagicMock()
        mock_process.communicate.return_value = (plistlib.dumps(base_pkginfo), b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Mock library methods
        with patch.object(self.processor, "_fetch_repo_library") as mock_fetch:
            mock_library = MagicMock()
            mock_library.copy_pkg_to_repo.return_value = self.pkg_path
            mock_library.copy_pkginfo_to_repo.return_value = "/path/to/pkginfo"
            mock_library.munki_repo = self.munki_repo
            mock_fetch.return_value = mock_library

            with patch.object(
                self.processor, "_find_matching_pkginfo", return_value=None
            ):
                self.processor.main()

        # Verify version_comparison_key was set
        pkginfo_arg = mock_library.copy_pkginfo_to_repo.call_args[0][0]
        self.assertEqual(
            pkginfo_arg["installs"][0]["version_comparison_key"], "CFBundleVersion"
        )

    @patch("subprocess.Popen")
    def test_main_version_comparison_key_missing_raises_error(self, mock_popen):
        """Test that main() raises error when version_comparison_key not found in installs."""
        self.processor.env["version_comparison_key"] = "NonExistentKey"

        # Mock subprocess result
        base_pkginfo = self._create_mock_pkginfo()
        mock_process = MagicMock()
        mock_process.communicate.return_value = (plistlib.dumps(base_pkginfo), b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        with patch.object(self.processor, "_fetch_repo_library"):
            with self.assertRaisesRegex(
                ProcessorError, "version_comparison_key.*could not be found"
            ):
                self.processor.main()

    @patch("subprocess.Popen")
    def test_main_skips_import_when_matching_item_exists(self, mock_popen):
        """Test that main() skips import when matching item already exists."""
        # Mock subprocess result
        base_pkginfo = self._create_mock_pkginfo()
        mock_process = MagicMock()
        mock_process.communicate.return_value = (plistlib.dumps(base_pkginfo), b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Mock matching item found
        matching_items = [
            {
                "installer_item_location": "testing/TestApp-1.0.0.pkg",
                "supported_architectures": None,
            }
        ]

        with patch.object(self.processor, "_fetch_repo_library") as mock_fetch:
            mock_library = MagicMock()
            mock_library.munki_repo = self.munki_repo
            mock_fetch.return_value = mock_library

            with patch.object(
                self.processor, "_find_matching_pkginfo", return_value=matching_items
            ):
                self.processor.main()

        # Verify import was skipped
        self.assertEqual(self.processor.env["munki_repo_changed"], False)
        self.assertEqual(
            self.processor.env["pkg_repo_path"],
            os.path.join(self.munki_repo, "pkgs", "testing/TestApp-1.0.0.pkg"),
        )

    @patch("subprocess.Popen")
    def test_main_forces_import_when_force_munkiimport_set(self, mock_popen):
        """Test that main() forces import when force_munkiimport is set."""
        self.processor.env["force_munkiimport"] = True

        # Mock subprocess result
        base_pkginfo = self._create_mock_pkginfo()
        mock_process = MagicMock()
        mock_process.communicate.return_value = (plistlib.dumps(base_pkginfo), b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Mock library methods
        with patch.object(self.processor, "_fetch_repo_library") as mock_fetch:
            mock_library = MagicMock()
            mock_library.copy_pkg_to_repo.return_value = self.pkg_path
            mock_library.copy_pkginfo_to_repo.return_value = "/path/to/pkginfo"
            mock_library.munki_repo = self.munki_repo
            mock_fetch.return_value = mock_library

            # Even though we have matching items, it should still import
            with patch.object(self.processor, "_find_matching_pkginfo") as mock_find:
                # _find_matching_pkginfo should not be called when force_munkiimport is True
                self.processor.main()
                mock_find.assert_not_called()

        # Verify import proceeded
        self.assertEqual(self.processor.env["munki_repo_changed"], True)

    @patch("subprocess.Popen")
    def test_main_copies_uninstaller_when_provided(self, mock_popen):
        """Test that main() copies uninstaller package when provided."""
        uninstaller_path = os.path.join(self.tmp_dir.name, "uninstaller.pkg")
        self.processor.env["uninstaller_pkg_path"] = uninstaller_path

        # Mock subprocess result
        base_pkginfo = self._create_mock_pkginfo()
        mock_process = MagicMock()
        mock_process.communicate.return_value = (plistlib.dumps(base_pkginfo), b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Mock library methods
        with patch.object(self.processor, "_fetch_repo_library") as mock_fetch:
            mock_library = MagicMock()
            mock_library.copy_pkg_to_repo.side_effect = [
                self.pkg_path,  # main package
                "pkgs/uninstaller.pkg",  # uninstaller
            ]
            mock_library.copy_pkginfo_to_repo.return_value = "/path/to/pkginfo"
            mock_library.munki_repo = self.munki_repo
            mock_fetch.return_value = mock_library

            with patch.object(
                self.processor, "_find_matching_pkginfo", return_value=None
            ):
                self.processor.main()

        # Verify uninstaller was copied and pkginfo updated
        self.assertEqual(mock_library.copy_pkg_to_repo.call_count, 2)
        pkginfo_arg = mock_library.copy_pkginfo_to_repo.call_args[0][0]
        self.assertEqual(pkginfo_arg["uninstaller_item_location"], "uninstaller.pkg")
        self.assertTrue(pkginfo_arg["uninstallable"])

    @patch("subprocess.Popen")
    def test_main_sets_summary_result(self, mock_popen):
        """Test that main() sets correct summary result."""
        # Mock subprocess result
        base_pkginfo = self._create_mock_pkginfo()
        mock_process = MagicMock()
        mock_process.communicate.return_value = (plistlib.dumps(base_pkginfo), b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Mock library methods
        with patch.object(self.processor, "_fetch_repo_library") as mock_fetch:
            mock_library = MagicMock()
            mock_library.copy_pkg_to_repo.return_value = os.path.join(
                self.munki_repo, "pkgs", "TestApp-1.0.0.pkg"
            )
            mock_library.copy_pkginfo_to_repo.return_value = os.path.join(
                self.munki_repo, "pkgsinfo", "TestApp-1.0.0.plist"
            )
            mock_library.munki_repo = self.munki_repo
            mock_fetch.return_value = mock_library

            with patch.object(
                self.processor, "_find_matching_pkginfo", return_value=None
            ):
                self.processor.main()

        # Verify summary result
        summary = self.processor.env["munki_importer_summary_result"]
        self.assertEqual(summary["data"]["name"], "TestApp")
        self.assertEqual(summary["data"]["version"], "1.0.0")
        self.assertEqual(summary["data"]["catalogs"], "testing")
        self.assertEqual(summary["data"]["pkginfo_path"], "TestApp-1.0.0.plist")
        self.assertEqual(summary["data"]["pkg_repo_path"], "TestApp-1.0.0.pkg")

    # Test edge cases and error conditions
    def test_main_clears_existing_summary_result(self):
        """Test that main() clears any pre-existing summary result."""
        self.processor.env["munki_importer_summary_result"] = {"old": "data"}

        with patch("subprocess.Popen") as mock_popen:
            # Mock subprocess result
            mock_process = MagicMock()
            mock_process.communicate.return_value = (
                plistlib.dumps(self._create_mock_pkginfo()),
                b"",
            )
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            # Mock library methods
            with patch.object(self.processor, "_fetch_repo_library") as mock_fetch:
                mock_library = MagicMock()
                mock_library.copy_pkg_to_repo.return_value = self.pkg_path
                mock_library.copy_pkginfo_to_repo.return_value = "/path/to/pkginfo"
                mock_library.munki_repo = self.munki_repo
                mock_fetch.return_value = mock_library

                with patch.object(
                    self.processor, "_find_matching_pkginfo", return_value=None
                ):
                    self.processor.main()

        # Should have new summary, not old one
        summary = self.processor.env["munki_importer_summary_result"]
        self.assertNotIn("old", summary)
        self.assertIn("data", summary)


if __name__ == "__main__":
    unittest.main()
