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
import tempfile
import unittest
from unittest.mock import patch

from autopkglib import ProcessorError
from autopkglib.PkgExtractor import PkgExtractor
from tests import get_processor_module

PkgExtractorModule = get_processor_module(PkgExtractor)


class TestPkgExtractor(unittest.TestCase):
    """Tests for PkgExtractor."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.processor = PkgExtractor()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _make_pkg(self, default_location="/"):
        pkg_path = os.path.join(self.tmp_dir.name, "Test.pkg")
        contents_path = os.path.join(pkg_path, "Contents")
        os.makedirs(contents_path)

        info = {"IFPkgFlagDefaultLocation": default_location}
        with open(os.path.join(contents_path, "Info.plist"), "wb") as f:
            plistlib.dump(info, f)
        with open(os.path.join(contents_path, "Archive.pax.gz"), "wb") as f:
            f.write(b"payload")

        return pkg_path

    @patch.object(PkgExtractorModule.subprocess, "Popen")
    def test_extract_payload_uses_default_location_under_extract_root(self, mock_popen):
        pkg_path = self._make_pkg("/Applications")
        extract_root = os.path.join(self.tmp_dir.name, "pkgroot")
        mock_popen.return_value.communicate.return_value = ("", "")
        mock_popen.return_value.returncode = 0

        self.processor.extract_payload(pkg_path, extract_root)

        expected_extract_path = os.path.join(extract_root, "Applications")
        self.assertTrue(os.path.isdir(expected_extract_path))
        command = mock_popen.call_args[0][0]
        self.assertEqual(command[-1], expected_extract_path)

    @patch.object(PkgExtractorModule.subprocess, "Popen")
    def test_extract_payload_rejects_parent_directory_escape(self, mock_popen):
        pkg_path = self._make_pkg("../escape")
        extract_root = os.path.join(self.tmp_dir.name, "pkgroot")
        os.makedirs(extract_root)
        marker = os.path.join(extract_root, "marker")
        with open(marker, "w", encoding="utf-8") as f:
            f.write("keep")

        with self.assertRaisesRegex(ProcessorError, "resolves outside extract_root"):
            self.processor.extract_payload(pkg_path, extract_root)

        mock_popen.assert_not_called()
        self.assertTrue(os.path.exists(marker))
        self.assertFalse(os.path.exists(os.path.join(self.tmp_dir.name, "escape")))

    @patch.object(PkgExtractorModule.subprocess, "Popen")
    def test_extract_payload_rejects_normalized_parent_escape(self, mock_popen):
        pkg_path = self._make_pkg("Applications/../../escape")
        extract_root = os.path.join(self.tmp_dir.name, "pkgroot")

        with self.assertRaisesRegex(ProcessorError, "resolves outside extract_root"):
            self.processor.extract_payload(pkg_path, extract_root)

        mock_popen.assert_not_called()
        self.assertFalse(os.path.exists(os.path.join(self.tmp_dir.name, "escape")))


if __name__ == "__main__":
    unittest.main()
