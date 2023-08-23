#!/usr/local/autopkg/python
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
from unittest.mock import patch

from autopkglib.PkgCopier import PkgCopier


class TestPkgCopier(unittest.TestCase):
    """Test class for PkgCopier Processor."""

    def setUp(self):
        self.good_env = {"source_pkg": "source.pkg", "pkg_path": "dest.pkg"}
        self.good_glob_dest_env = {"source_pkg": "source*", "pkg_path": "dest.pkg"}
        self.good_glob_env = {"source_pkg": "source*"}
        self.bad_env = {}
        self.input_plist = plistlib.dumps(self.good_env)
        self.processor = PkgCopier(infile=self.input_plist)

    def tearDown(self):
        pass

    @patch("autopkglib.PkgCopier.copy")
    @patch("autopkglib.glob.glob")
    def test_no_fail_if_good_env(self, mock_glob, mock_copy):
        """The processor should not raise any exceptions if run normally."""
        self.processor.env = self.good_env
        mock_glob.return_value = ["source.pkg"]
        self.processor.main()

    @patch("autopkglib.PkgCopier.copy")
    @patch("autopkglib.glob.glob")
    def test_no_pkgpath_uses_source_name(self, mock_glob, mock_copy):
        """If pkg_path is not specified, it should use the source name."""
        self.processor.env = self.good_glob_env
        self.processor.env["RECIPE_CACHE_DIR"] = "fake_cache_dir"
        mock_glob.return_value = ["source.pkg"]
        self.processor.main()
        mock_copy.assert_called_with(
            "source.pkg",
            os.path.join(self.processor.env["RECIPE_CACHE_DIR"], "source.pkg"),
            overwrite=True,
        )

    @patch("autopkglib.PkgCopier.copy")
    @patch("autopkglib.glob.glob")
    def test_no_pkgpath_uses_dest_name(self, mock_glob, mock_copy):
        """If pkg_path is specified, it should be used."""
        self.processor.env = self.good_glob_dest_env
        mock_glob.return_value = ["source.pkg"]
        self.processor.main()
        mock_copy.assert_called_with(
            "source.pkg", self.processor.env["pkg_path"], overwrite=True
        )


if __name__ == "__main__":
    unittest.main()
