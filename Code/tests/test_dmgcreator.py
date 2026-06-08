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

import unittest

from autopkglib import ProcessorError
from autopkglib.DmgCreator import DEFAULT_DMG_FILESYSTEM, DEFAULT_DMG_FORMAT, DmgCreator


class TestDmgCreatorDefaults(unittest.TestCase):
    """Verify that PR #905 changed the default DMG format and filesystem."""

    def test_default_format_is_ulfo(self):
        self.assertEqual(DEFAULT_DMG_FORMAT, "ULFO")

    def test_default_filesystem_is_apfs(self):
        self.assertEqual(DEFAULT_DMG_FILESYSTEM, "APFS")


class TestDmgCreatorFormatValidation(unittest.TestCase):
    """Format and filesystem validation raises ProcessorError before any
    subprocess call, so these tests need no mocking."""

    def setUp(self):
        self.processor = DmgCreator()
        self.processor.env = {
            "dmg_root": "/tmp/fake_root",
            "dmg_path": "/tmp/fake.dmg",
        }

    def test_invalid_format_raises(self):
        self.processor.env["dmg_format"] = "BOGUS"
        with self.assertRaises(ProcessorError):
            self.processor.main()

    def test_invalid_filesystem_raises(self):
        self.processor.env["dmg_filesystem"] = "NTFS"
        with self.assertRaises(ProcessorError):
            self.processor.main()

    def test_invalid_zlib_level_raises(self):
        self.processor.env["dmg_zlib_level"] = "10"
        with self.assertRaises(ProcessorError):
            self.processor.main()


if __name__ == "__main__":
    unittest.main()
