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
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch

from autopkglib import ProcessorError
from autopkglib.Symlinker import Symlinker


class TestSymlinker(unittest.TestCase):
    """Tests for Symlinker."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.processor = Symlinker()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _path(self, name):
        return os.path.join(self.tmp_dir.name, name)

    def _write_source_file(self):
        source_path = self._path("source.txt")
        with open(source_path, "w") as f:
            f.write("source")
        return source_path

    def _readlink_target(self, path):
        target = os.readlink(path)
        if target.startswith("\\\\?\\UNC\\"):
            return "\\" + target[7:]
        if target.startswith("\\\\?\\"):
            return target[4:]
        return target

    def test_symlink_created_successfully(self):
        source_path = self._write_source_file()
        destination_path = self._path("destination.txt")
        self.processor.env = {
            "source_path": source_path,
            "destination_path": destination_path,
        }

        self.processor.main()

        self.assertTrue(os.path.islink(destination_path))
        self.assertEqual(self._readlink_target(destination_path), source_path)

    def test_overwrite_removes_existing_destination_first(self):
        source_path = self._write_source_file()
        destination_path = self._path("destination.txt")
        with open(destination_path, "w") as f:
            f.write("existing")
        self.processor.env = {
            "source_path": source_path,
            "destination_path": destination_path,
            "overwrite": True,
        }

        self.processor.main()

        self.assertTrue(os.path.islink(destination_path))
        self.assertEqual(self._readlink_target(destination_path), source_path)

    def test_oserror_on_unlink_raises_processor_error(self):
        source_path = self._write_source_file()
        destination_path = self._path("destination.txt")
        with open(destination_path, "w") as f:
            f.write("existing")
        self.processor.env = {
            "source_path": source_path,
            "destination_path": destination_path,
            "overwrite": True,
        }

        with (
            patch("os.unlink", side_effect=OSError("permission denied")),
            self.assertRaisesRegex(ProcessorError, "Can't remove"),
        ):
            self.processor.main()

    def test_symlink_failure_raises_processor_error(self):
        source_path = self._write_source_file()
        destination_path = self._path("destination.txt")
        self.processor.env = {
            "source_path": source_path,
            "destination_path": destination_path,
        }

        with (
            patch("os.symlink", side_effect=OSError("permission denied")),
            self.assertRaisesRegex(ProcessorError, "Can't symlink"),
        ):
            self.processor.main()


if __name__ == "__main__":
    unittest.main()
