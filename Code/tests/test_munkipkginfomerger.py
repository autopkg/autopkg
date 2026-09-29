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
from unittest.mock import patch

from autopkglib.MunkiPkginfoMerger import MunkiPkginfoMerger


class TestMunkiPkginfoMerger(unittest.TestCase):
    """Test class for MunkiPkginfoMerger Processor."""

    def setUp(self):
        self.processor = MunkiPkginfoMerger()
        self.processor.env = {}

    def test_init_pkginfo_when_missing(self):
        self.processor.env = {"additional_pkginfo": {"foo": "bar"}}

        self.processor.main()

        self.assertIn("pkginfo", self.processor.env)
        self.assertIsInstance(self.processor.env["pkginfo"], dict)
        self.assertEqual(self.processor.env["pkginfo"]["foo"], "bar")

    def test_merge_into_existing_pkginfo(self):
        self.processor.env = {
            "pkginfo": {"existing_key": "value1"},
            "additional_pkginfo": {
                "merged_key": "value2",
                "existing_key": "updated",
            },
        }

        self.processor.main()

        self.assertEqual(self.processor.env["pkginfo"]["merged_key"], "value2")
        self.assertEqual(self.processor.env["pkginfo"]["existing_key"], "updated")

    def test_merge_empty_additional_pkginfo(self):
        self.processor.env = {
            "pkginfo": {"original": "data"},
            "additional_pkginfo": {},
        }

        self.processor.main()

        self.assertEqual(self.processor.env["pkginfo"], {"original": "data"})

    def test_output_message_on_merge(self):
        additional_pkginfo = {"test_key": "test_value"}
        self.processor.env = {"additional_pkginfo": additional_pkginfo}

        with patch.object(self.processor, "output") as mock_output:
            self.processor.main()

        mock_output.assert_called_once()
        message = mock_output.call_args[0][0]
        self.assertIn("Merged", message)
        self.assertIn(str(additional_pkginfo), message)


if __name__ == "__main__":
    unittest.main()
