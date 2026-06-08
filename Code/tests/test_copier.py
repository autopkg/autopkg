#!/usr/local/autopkg/python
#
# Copyright 2019 Nick McSpadden
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
import plistlib
import tempfile
import unittest
from unittest.mock import patch

from autopkglib import ProcessorError
from autopkglib.Copier import Copier


class TestCopier(unittest.TestCase):
    """Test class for FileFinder Processor."""

    def setUp(self):
        self.good_env = {
            "source_path": "source",
            "destination_path": "dest",
            "overwrite": True,
        }
        self.glob_env = {
            "source_path": "dir/source*",
            "destination_path": "dest",
            "overwrite": True,
        }
        self.dmg_env = {
            "source_path": "mydmg.dmg/source",
            "destination_path": "dest",
            "overwrite": True,
        }
        self.dmg_glob_env = {
            "source_path": "mydmg.dmg/source*",
            "destination_path": "dest",
            "overwrite": True,
        }
        self.bad_env = {"source_path": "source"}
        self.input_plist = plistlib.dumps(self.good_env)
        self.processor = Copier(infile=self.input_plist)

    def tearDown(self):
        pass

    def _copy(self, source_path, destination_path, overwrite=False):
        with patch.object(self.processor, "output"):
            self.processor.copy(source_path, destination_path, overwrite=overwrite)

    def test_raise_if_no_dest(self):
        """Raise an exception if missing a critical input variable."""
        self.processor.env = self.bad_env
        with self.assertRaises(ProcessorError):
            self.processor.main()

    @patch("autopkglib.glob.glob")
    @patch.object(Copier, "copy")
    def test_no_fail_if_good_env(self, mock_copy, mock_glob):
        """The processor should not raise any exceptions if run normally."""
        self.processor.env = self.good_env
        mock_glob.return_value = ["source"]
        mock_copy.return_value = True
        self.processor.main()
        mock_copy.assert_called_once()

    @patch("autopkglib.glob.glob")
    @patch.object(Copier, "copy")
    def test_no_fail_if_glob_env(self, mock_copy, mock_glob):
        """The processor should not raise any exceptions if run with a glob."""
        self.processor.env = self.glob_env
        mock_glob.return_value = ["source"]
        mock_copy.return_value = True
        self.processor.main()
        mock_copy.assert_called_once()

    @patch.object(Copier, "unmount_if_mounted")
    @patch.object(Copier, "mount")
    @patch("autopkglib.glob.glob")
    @patch.object(Copier, "copy")
    def test_no_fail_if_dmg_env(self, mock_copy, mock_glob, mock_mount, mock_unmount):
        """The processor should not raise any exceptions if run with a DMG."""
        self.processor.env = self.dmg_env
        mock_glob.return_value = ["/fake/mount/source"]
        mock_copy.return_value = True
        mock_mount.return_value = "/fake/mount"
        self.processor.main()
        mock_copy.assert_called_once()
        mock_unmount.assert_called_once()

    @patch.object(Copier, "unmount_if_mounted")
    @patch.object(Copier, "mount")
    @patch("autopkglib.glob.glob")
    @patch.object(Copier, "copy")
    def test_no_fail_if_dmg_glob_env(
        self, mock_copy, mock_glob, mock_mount, mock_unmount
    ):
        """The processor should not raise any exceptions if run with a DMG and glob."""
        self.processor.env = self.dmg_glob_env
        mock_glob.return_value = ["/fake/mount/source"]
        mock_copy.return_value = True
        mock_mount.return_value = "/fake/mount"
        self.processor.main()
        mock_copy.assert_called_once()
        mock_unmount.assert_called_once()

    @patch("autopkglib.glob.glob")
    @patch.object(Copier, "copy")
    def test_multiple_matches(self, mock_copy, mock_glob):
        """The processor should not raise any exceptions if run with a glob."""
        self.processor.env = self.glob_env
        mock_glob.return_value = ["source1", "source2"]
        mock_copy.return_value = True
        self.processor.main()
        mock_copy.assert_called_once_with(
            "source1", self.glob_env["destination_path"], overwrite=True
        )

    def test_copy_file_over_existing_directory(self):
        """copy replaces an existing directory with a source file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_path = os.path.join(tmp_dir, "source.txt")
            destination_path = os.path.join(tmp_dir, "dest")
            os.makedirs(destination_path)
            with open(source_path, "w") as f:
                f.write("source")
            with open(os.path.join(destination_path, "old.txt"), "w") as f:
                f.write("old")

            self._copy(source_path, destination_path, overwrite=True)

            self.assertTrue(os.path.isfile(destination_path))
            with open(destination_path) as f:
                self.assertEqual(f.read(), "source")

    def test_copy_directory_over_existing_file(self):
        """copy replaces an existing file with a source directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_path = os.path.join(tmp_dir, "source")
            destination_path = os.path.join(tmp_dir, "dest")
            os.makedirs(source_path)
            with open(os.path.join(source_path, "source.txt"), "w") as f:
                f.write("source")
            with open(destination_path, "w") as f:
                f.write("old")

            self._copy(source_path, destination_path, overwrite=True)

            self.assertTrue(os.path.isdir(destination_path))
            with open(os.path.join(destination_path, "source.txt")) as f:
                self.assertEqual(f.read(), "source")

    def test_copy_removal_oserror_raises_processor_error(self):
        """copy wraps OSError raised while removing an existing destination."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_path = os.path.join(tmp_dir, "source.txt")
            destination_path = os.path.join(tmp_dir, "dest.txt")
            with open(source_path, "w") as f:
                f.write("source")
            with open(destination_path, "w") as f:
                f.write("old")

            with (
                patch("os.unlink", side_effect=OSError("permission denied")),
                self.assertRaisesRegex(ProcessorError, "Can't remove"),
            ):
                self._copy(source_path, destination_path, overwrite=True)

    def test_copy_directory_to_new_path(self):
        """copy copies a source directory tree to the destination."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_path = os.path.join(tmp_dir, "source")
            destination_path = os.path.join(tmp_dir, "dest")
            os.makedirs(os.path.join(source_path, "nested"))
            with open(os.path.join(source_path, "nested", "file.txt"), "w") as f:
                f.write("source")

            self._copy(source_path, destination_path)

            with open(os.path.join(destination_path, "nested", "file.txt")) as f:
                self.assertEqual(f.read(), "source")

    def test_copy_file_to_new_path(self):
        """copy copies a source file to a file destination."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_path = os.path.join(tmp_dir, "source.txt")
            destination_path = os.path.join(tmp_dir, "dest.txt")
            with open(source_path, "w") as f:
                f.write("source")

            self._copy(source_path, destination_path)

            with open(destination_path) as f:
                self.assertEqual(f.read(), "source")

    def test_copy_file_into_existing_directory(self):
        """copy copies a source file into an existing destination directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_path = os.path.join(tmp_dir, "source.txt")
            destination_path = os.path.join(tmp_dir, "dest")
            os.makedirs(destination_path)
            with open(source_path, "w") as f:
                f.write("source")

            self._copy(source_path, destination_path)

            with open(os.path.join(destination_path, "source.txt")) as f:
                self.assertEqual(f.read(), "source")

    def test_copy_baseexception_raises_processor_error(self):
        """copy wraps copy failures in ProcessorError."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_path = os.path.join(tmp_dir, "source.txt")
            destination_path = os.path.join(tmp_dir, "missing", "dest.txt")
            with open(source_path, "w") as f:
                f.write("source")

            with self.assertRaisesRegex(ProcessorError, "Can't copy"):
                self._copy(source_path, destination_path)


if __name__ == "__main__":
    unittest.main()
