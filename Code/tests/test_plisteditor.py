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
import plistlib
import unittest
from tempfile import TemporaryDirectory

from autopkglib import ProcessorError
from autopkglib.PlistEditor import PlistEditor


class TestPlistEditor(unittest.TestCase):
    """Tests for PlistEditor."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.processor = PlistEditor()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _plist_path(self, name="test.plist"):
        return os.path.join(self.tmp_dir.name, name)

    def _write_plist(self, data, name="test.plist"):
        plist_path = self._plist_path(name)
        with open(plist_path, "wb") as f:
            plistlib.dump(data, f)
        return plist_path

    def test_read_plist_reads_real_path(self):
        plist_path = self._write_plist({"existing": "value"})

        self.assertEqual(self.processor.read_plist(plist_path), {"existing": "value"})

    def test_read_plist_returns_empty_dict_for_empty_path(self):
        self.assertEqual(self.processor.read_plist(None), {})
        self.assertEqual(self.processor.read_plist(""), {})

    def test_read_plist_raises_processor_error_for_bad_path(self):
        with self.assertRaisesRegex(ProcessorError, "Could not read"):
            self.processor.read_plist(self._plist_path("missing.plist"))

    def test_write_plist_writes_data(self):
        plist_path = self._plist_path("output.plist")

        self.processor.write_plist({"created": True}, plist_path)

        with open(plist_path, "rb") as f:
            self.assertEqual(plistlib.load(f), {"created": True})

    def test_write_plist_raises_processor_error_for_bad_path(self):
        with self.assertRaisesRegex(ProcessorError, "Could not write"):
            self.processor.write_plist(
                {"created": True},
                os.path.join(self.tmp_dir.name, "missing", "output.plist"),
            )

    def test_main_merges_plist_data_into_existing_plist(self):
        input_path = self._write_plist({"existing": "value", "replace": "old"})
        output_path = self._plist_path("output.plist")
        self.processor.env = {
            "input_plist_path": input_path,
            "output_plist_path": output_path,
            "plist_data": {"added": "new", "replace": "new"},
        }

        self.processor.main()

        with open(output_path, "rb") as f:
            self.assertEqual(
                plistlib.load(f),
                {"existing": "value", "added": "new", "replace": "new"},
            )

    def test_main_writes_plist_data_without_input_plist_path(self):
        output_path = self._plist_path("output.plist")
        self.processor.env = {
            "output_plist_path": output_path,
            "plist_data": {"created": True},
        }

        self.processor.main()

        with open(output_path, "rb") as f:
            self.assertEqual(plistlib.load(f), {"created": True})


if __name__ == "__main__":
    unittest.main()
