#!/Library/AutoPkg/Python3/Python.framework/Versions/Current/bin/python3

import os
import plistlib
import unittest
from unittest.mock import patch

from autopkglib.PkgCopier import PkgCopier


class TestPkgCopier(unittest.TestCase):
    """Test class for PkgCopier Processor."""

    def setUp(self):
        self.good_env = {"source_pkg": "source", "pkg_path": "dest"}
        self.good_glob_dest_env = {"source_pkg": "source*", "pkg_path": "dest"}
        self.good_glob_env = {"source_pkg": "source*"}
        self.bad_env = {}
        self.input_plist = plistlib.dumps(self.good_env)
        self.processor = PkgCopier(infile=self.input_plist)

    def tearDown(self):
        pass

    @patch("autopkglib.PkgCopier.copy")
    @patch("glob.glob")
    def test_no_fail_if_good_env(self, mock_glob, mock_copy):
        """The processor should not raise any exceptions if run normally."""
        self.processor.env = self.good_env
        mock_glob.return_value = ["source"]
        self.processor.main()

    @patch("autopkglib.PkgCopier.copy")
    @patch("glob.glob")
    def test_no_pkgpath_uses_source_name(self, mock_glob, mock_copy):
        """If pkg_path is not specified, it should use the source name."""
        self.processor.env = self.good_glob_env
        self.processor.env["RECIPE_CACHE_DIR"] = "fake_cache_dir"
        mock_glob.return_value = ["source"]
        self.processor.main()
        mock_copy.assert_called_with(
            "source",
            os.path.join(self.processor.env["RECIPE_CACHE_DIR"], "source"),
            overwrite=True,
        )

    @patch("autopkglib.PkgCopier.copy")
    @patch("glob.glob")
    def test_no_pkgpath_uses_dest_name(self, mock_glob, mock_copy):
        """If pkg_path is specified, it should be used."""
        self.processor.env = self.good_glob_dest_env
        mock_glob.return_value = ["source"]
        self.processor.main()
        mock_copy.assert_called_with(
            "source", self.processor.env["pkg_path"], overwrite=True
        )


if __name__ == "__main__":
    unittest.main()
