#!/usr/local/autopkg/python
#
# Copyright 2026 Elliot Jordan
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
        # Windows doesn't honor POSIX permission bits, so only assert the
        # exact modes where they're meaningful.
        if os.name != "nt":
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
