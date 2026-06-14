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

import sys
import unittest
from unittest.mock import patch

from autopkglib.MunkiSetDefaultCatalog import MunkiSetDefaultCatalog


@unittest.skipUnless(sys.platform == "darwin", "Munki is macOS-only")
class TestMunkiSetDefaultCatalog(unittest.TestCase):
    """Test class for MunkiSetDefaultCatalog Processor."""

    def setUp(self):
        self.processor = MunkiSetDefaultCatalog()
        self.processor.env = {}

    @patch(
        "autopkglib.MunkiSetDefaultCatalog.CFPreferencesCopyAppValue", return_value=None
    )
    def test_initializes_missing_pkginfo(self, mock_pref):
        """Missing pkginfo key is initialized to an empty dict."""
        # no 'pkginfo' key in env
        self.processor.env = {}
        self.processor.main()
        self.assertIn("pkginfo", self.processor.env)
        self.assertEqual(self.processor.env["pkginfo"], {})

    @patch(
        "autopkglib.MunkiSetDefaultCatalog.CFPreferencesCopyAppValue",
        return_value="production",
    )
    def test_sets_catalogs_when_default_found(self, mock_pref):
        """catalogs key is set to [default_catalog] when a default is found."""
        self.processor.env = {"pkginfo": {}}
        with patch.object(self.processor, "output") as mock_output:
            self.processor.main()
        self.assertEqual(self.processor.env["pkginfo"]["catalogs"], ["production"])
        args, _ = mock_output.call_args
        self.assertIn("production", args[0])

    @patch(
        "autopkglib.MunkiSetDefaultCatalog.CFPreferencesCopyAppValue", return_value=None
    )
    def test_preserves_pkginfo_when_no_default(self, mock_pref):
        """Existing pkginfo is unchanged when no default catalog is set."""
        self.processor.env = {"pkginfo": {"name": "TestApp"}}
        with patch.object(self.processor, "output") as mock_output:
            self.processor.main()
        self.assertEqual(self.processor.env["pkginfo"], {"name": "TestApp"})
        args, _ = mock_output.call_args
        self.assertIn("No default catalogs found", args[0])

    @patch(
        "autopkglib.MunkiSetDefaultCatalog.CFPreferencesCopyAppValue",
        return_value="staging",
    )
    def test_overwrites_existing_catalogs(self, mock_pref):
        """Existing catalogs value is overwritten by the configured default."""
        self.processor.env = {"pkginfo": {"catalogs": ["existing_catalog"]}}
        self.processor.main()
        self.assertEqual(self.processor.env["pkginfo"]["catalogs"], ["staging"])

    @patch(
        "autopkglib.MunkiSetDefaultCatalog.CFPreferencesCopyAppValue",
        return_value="testing",
    )
    def test_output_called_with_correct_message(self, mock_pref):
        """output() is called once with a message containing the catalog name."""
        self.processor.env = {"pkginfo": {}}
        with patch.object(self.processor, "output") as mock_output:
            self.processor.main()
        mock_output.assert_called_once()
        args, _ = mock_output.call_args
        self.assertIn("Updated target catalogs", args[0])
        self.assertIn("testing", args[0])

    @patch(
        "autopkglib.MunkiSetDefaultCatalog.CFPreferencesCopyAppValue", return_value=None
    )
    def test_no_output_call_when_no_catalog(self, mock_pref):
        """output() is called once with the 'nothing changed' message when no default."""
        self.processor.env = {"pkginfo": {}}
        with patch.object(self.processor, "output") as mock_output:
            self.processor.main()
        mock_output.assert_called_once_with(
            "No default catalogs found, nothing changed"
        )
        self.assertNotIn("catalogs", self.processor.env["pkginfo"])


if __name__ == "__main__":
    unittest.main()
