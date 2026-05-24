#!/usr/local/autopkg/python

import os
import plistlib
import sys
import unittest
from copy import deepcopy
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from autopkglib import ProcessorError
from autopkglib.MunkiOptionalReceiptEditor import MunkiOptionalReceiptEditor

_receipt_editor_mod = sys.modules["autopkglib.MunkiOptionalReceiptEditor"]


@unittest.skipUnless(sys.platform == "darwin", "Munki is macOS-only")
class TestMunkiOptionalReceiptEditor(unittest.TestCase):
    """Test class for MunkiOptionalReceiptEditor Processor."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.munki_repo = os.path.join(self.tmp_dir.name, "munki_repo")
        os.makedirs(os.path.join(self.munki_repo, "pkgsinfo"))

        self.pkginfo = {
            "name": "TestApp",
            "version": "1.0.0",
            "catalogs": ["testing"],
            "receipts": [
                {"packageid": "com.example.app", "version": "1.0.0"},
                {"packageid": "com.example.helper", "version": "1.0.0"},
                {"packageid": "com.example.extra", "version": "1.0.0"},
            ],
        }

        self.pkginfo_path = os.path.join(
            self.munki_repo, "pkgsinfo", "TestApp-1.0.0.plist"
        )
        with open(self.pkginfo_path, "wb") as f:
            plistlib.dump(self.pkginfo, f)

        self.good_env = {
            "pkginfo_repo_path": self.pkginfo_path,
            "pkg_ids_set_optional_true": ["com.example.helper"],
            "MUNKI_REPO": self.munki_repo,
            "MUNKI_REPO_PLUGIN": "FileRepo",
            "MUNKILIB_DIR": "/usr/local/munki",
            "force_munki_repo_lib": False,
        }

        self.processor = MunkiOptionalReceiptEditor()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_sets_receipt_optional(self):
        """Matching receipts are set to optional=True."""
        self.processor.env = deepcopy(self.good_env)
        self.processor.main()

        with open(self.pkginfo_path, "rb") as f:
            result = plistlib.load(f)

        self.assertFalse(result["receipts"][0].get("optional", False))
        self.assertTrue(result["receipts"][1]["optional"])
        self.assertFalse(result["receipts"][2].get("optional", False))

    def test_sets_multiple_receipts_optional(self):
        """Multiple matching receipts are all set to optional."""
        self.processor.env = deepcopy(self.good_env)
        self.processor.env["pkg_ids_set_optional_true"] = [
            "com.example.app",
            "com.example.extra",
        ]
        self.processor.main()

        with open(self.pkginfo_path, "rb") as f:
            result = plistlib.load(f)

        self.assertTrue(result["receipts"][0]["optional"])
        self.assertFalse(result["receipts"][1].get("optional", False))
        self.assertTrue(result["receipts"][2]["optional"])

    def test_no_matching_receipts_does_not_write(self):
        """When no receipts match, the file is not rewritten."""
        self.processor.env = deepcopy(self.good_env)
        self.processor.env["pkg_ids_set_optional_true"] = ["com.nonexistent.app"]

        mtime_before = os.path.getmtime(self.pkginfo_path)
        self.processor.main()
        mtime_after = os.path.getmtime(self.pkginfo_path)

        self.assertEqual(mtime_before, mtime_after)

    def test_no_receipts_raises_error(self):
        """Raises ProcessorError when pkginfo has no receipts key."""
        pkginfo_no_receipts = {"name": "TestApp", "version": "1.0.0"}
        with open(self.pkginfo_path, "wb") as f:
            plistlib.dump(pkginfo_no_receipts, f)

        self.processor.env = deepcopy(self.good_env)

        with self.assertRaises(ProcessorError):
            self.processor.main()

    def test_empty_pkginfo_repo_path_skips(self):
        """Empty pkginfo_repo_path causes early return."""
        self.processor.env = deepcopy(self.good_env)
        self.processor.env["pkginfo_repo_path"] = ""
        self.processor.main()

    def test_reads_from_munki_info_when_available(self):
        """Uses in-memory munki_info instead of reading from disk."""
        self.processor.env = deepcopy(self.good_env)
        in_memory_pkginfo = deepcopy(self.pkginfo)
        in_memory_pkginfo["receipts"][0]["version"] = "9.9.9"
        self.processor.env["munki_info"] = in_memory_pkginfo

        self.processor.main()

        with open(self.pkginfo_path, "rb") as f:
            result = plistlib.load(f)

        self.assertEqual(result["receipts"][0]["version"], "9.9.9")
        self.assertTrue(result["receipts"][1]["optional"])

    def test_updates_munki_info_in_env(self):
        """After modifying, munki_info is updated in the environment."""
        self.processor.env = deepcopy(self.good_env)
        self.processor.main()

        self.assertIn("munki_info", self.processor.env)
        self.assertTrue(self.processor.env["munki_info"]["receipts"][1]["optional"])

    def test_sets_munki_info_when_no_receipts_modified(self):
        """munki_info is set even when no receipts match."""
        self.processor.env = deepcopy(self.good_env)
        self.processor.env["pkg_ids_set_optional_true"] = ["com.nonexistent.app"]
        self.processor.main()

        self.assertIn("munki_info", self.processor.env)
        self.assertEqual(
            self.processor.env["munki_info"]["receipts"], self.pkginfo["receipts"]
        )

    @patch.object(_receipt_editor_mod, "fetch_repo_library")
    def test_writes_through_repo_library(self, mock_fetch):
        """Write is routed through the repo library, not raw open()."""
        mock_library = MagicMock()
        mock_fetch.return_value = mock_library

        self.processor.env = deepcopy(self.good_env)
        self.processor.main()

        mock_library.put_pkginfo_to_repo.assert_called_once()
        args = mock_library.put_pkginfo_to_repo.call_args
        written_pkginfo = args[0][0]
        written_path = args[0][1]

        self.assertTrue(written_pkginfo["receipts"][1]["optional"])
        self.assertEqual(written_path, self.pkginfo_path)


if __name__ == "__main__":
    unittest.main()
