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
from autopkglib.PathDeleter import PathDeleter


class TestPathDeleter(unittest.TestCase):
    """Tests for PathDeleter."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.processor = PathDeleter()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _path(self, name):
        return os.path.join(self.tmp_dir.name, name)

    def test_single_string_path_list_is_coerced_to_list(self):
        test_file = self._path("test.txt")
        with open(test_file, "w") as f:
            f.write("delete me")
        self.processor.env = {"path_list": test_file}

        self.processor.main()

        self.assertEqual(self.processor.env["path_list"], [test_file])
        self.assertFalse(os.path.exists(test_file))

    def test_deletes_file(self):
        test_file = self._path("test.txt")
        with open(test_file, "w") as f:
            f.write("delete me")
        self.processor.env = {"path_list": [test_file]}

        self.processor.main()

        self.assertFalse(os.path.exists(test_file))

    def test_deletes_symlink(self):
        target = self._path("target.txt")
        link = self._path("link.txt")
        with open(target, "w") as f:
            f.write("keep me")
        os.symlink(target, link)
        self.processor.env = {"path_list": [link]}

        self.processor.main()

        self.assertFalse(os.path.lexists(link))
        self.assertTrue(os.path.exists(target))

    def test_deletes_directory(self):
        test_dir = self._path("testdir")
        os.makedirs(test_dir)
        with open(os.path.join(test_dir, "file.txt"), "w") as f:
            f.write("delete me")
        self.processor.env = {"path_list": [test_dir]}

        self.processor.main()

        self.assertFalse(os.path.exists(test_dir))

    def test_nonexistent_path_raises_processor_error(self):
        missing_path = self._path("missing")
        self.processor.env = {"path_list": [missing_path]}

        with self.assertRaisesRegex(ProcessorError, "does not exist"):
            self.processor.main()

    def test_oserror_during_removal_raises_processor_error(self):
        test_file = self._path("test.txt")
        with open(test_file, "w") as f:
            f.write("delete me")
        self.processor.env = {"path_list": [test_file]}

        with (
            patch("os.remove", side_effect=OSError("permission denied")),
            self.assertRaisesRegex(ProcessorError, "Could not remove"),
        ):
            self.processor.main()


if __name__ == "__main__":
    unittest.main()
