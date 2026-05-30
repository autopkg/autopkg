#!/usr/local/autopkg/python

import os
import stat
import tempfile
import unittest

from autopkglib import ProcessorError
from autopkglib.PkgRootCreator import PkgRootCreator


class TestPkgRootCreator(unittest.TestCase):
    """Tests for PkgRootCreator."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.pkgroot = os.path.join(self.tmp_dir.name, "pkgroot")
        self.processor = PkgRootCreator()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _run_with_pkgdirs(self, pkgdirs):
        self.processor.env = {
            "pkgroot": self.pkgroot,
            "pkgdirs": pkgdirs,
        }
        self.processor.main()

    def test_creates_directories_under_pkgroot(self):
        self._run_with_pkgdirs(
            {
                "Applications": "0755",
                "Library/Application Support/Test": "0775",
            }
        )

        applications_path = os.path.join(self.pkgroot, "Applications")
        support_path = os.path.join(
            self.pkgroot, "Library", "Application Support", "Test"
        )

        self.assertTrue(os.path.isdir(applications_path))
        self.assertTrue(os.path.isdir(support_path))
        self.assertEqual(stat.S_IMODE(os.stat(applications_path).st_mode), 0o755)
        self.assertEqual(stat.S_IMODE(os.stat(support_path).st_mode), 0o775)

    def test_rejects_absolute_directory(self):
        outside_path = os.path.join(self.tmp_dir.name, "outside")

        with self.assertRaisesRegex(ProcessorError, "is absolute"):
            self._run_with_pkgdirs({outside_path: "0755"})

        self.assertFalse(os.path.exists(outside_path))

    def test_rejects_parent_directory_escape(self):
        outside_path = os.path.join(self.tmp_dir.name, "escape")

        with self.assertRaisesRegex(ProcessorError, "outside pkgroot"):
            self._run_with_pkgdirs({"../escape": "0755"})

        self.assertFalse(os.path.exists(outside_path))

    def test_rejects_sibling_prefix_escape(self):
        outside_path = os.path.join(self.tmp_dir.name, "pkgroot-evil")

        with self.assertRaisesRegex(ProcessorError, "outside pkgroot"):
            self._run_with_pkgdirs({"../pkgroot-evil": "0755"})

        self.assertFalse(os.path.exists(outside_path))

    def test_rejects_normalized_parent_directory_escape(self):
        outside_path = os.path.join(self.tmp_dir.name, "escape")

        with self.assertRaisesRegex(ProcessorError, "outside pkgroot"):
            self._run_with_pkgdirs({"Applications/../../escape": "0755"})

        self.assertFalse(os.path.exists(outside_path))


if __name__ == "__main__":
    unittest.main()
