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
import sys
import tempfile
import unittest
from unittest.mock import patch

from autopkglib import ProcessorError
from autopkglib.PkgRootCreator import PkgRootCreator


class TestPkgRootCreator(unittest.TestCase):
    """Tests for PkgRootCreator."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.pkgroot = os.path.join(self.tmp_dir.name, "pkgroot")
        self.processor = PkgRootCreator()
        self.module = sys.modules[PkgRootCreator.__module__]

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

    def test_removes_existing_symlink_pkgroot(self):
        target_path = os.path.join(self.tmp_dir.name, "target")
        os.mkdir(target_path)
        os.symlink(target_path, self.pkgroot)

        self._run_with_pkgdirs({})

        self.assertFalse(os.path.islink(self.pkgroot))
        self.assertTrue(os.path.isdir(self.pkgroot))

    def test_removes_existing_file_pkgroot(self):
        with open(self.pkgroot, "w", encoding="utf-8") as file_handle:
            file_handle.write("existing file")

        self._run_with_pkgdirs({})

        self.assertTrue(os.path.isdir(self.pkgroot))

    def test_removes_existing_directory_pkgroot(self):
        os.makedirs(self.pkgroot)
        existing_file = os.path.join(self.pkgroot, "existing")
        with open(existing_file, "w", encoding="utf-8") as file_handle:
            file_handle.write("existing file")

        self._run_with_pkgdirs({})

        self.assertTrue(os.path.isdir(self.pkgroot))
        self.assertEqual(os.listdir(self.pkgroot), [])

    def test_oserror_removing_pkgroot_raises_processor_error(self):
        with patch.object(self.module.os.path, "isfile", return_value=False):
            with patch.object(self.module.os.path, "isdir", return_value=True):
                with patch.object(
                    self.module.shutil,
                    "rmtree",
                    side_effect=OSError("permission denied"),
                ):
                    with self.assertRaisesRegex(ProcessorError, "Can't remove"):
                        self._run_with_pkgdirs({})

    def test_oserror_creating_pkgroot_raises_processor_error(self):
        self.pkgroot = os.path.join(
            self.tmp_dir.name, "nonexistent", "parent", "pkgroot"
        )

        with patch.object(
            self.module.os,
            "makedirs",
            side_effect=OSError("permission denied"),
        ):
            with self.assertRaisesRegex(ProcessorError, "Can't create"):
                self._run_with_pkgdirs({})

    def test_oserror_during_chmod_raises_processor_error(self):
        with patch.object(
            self.module.os,
            "chmod",
            side_effect=OSError("operation not permitted"),
        ):
            with self.assertRaisesRegex(
                ProcessorError,
                r"Can't create.*testdir.*mode",
            ):
                self._run_with_pkgdirs({"testdir": "0755"})


if __name__ == "__main__":
    unittest.main()
