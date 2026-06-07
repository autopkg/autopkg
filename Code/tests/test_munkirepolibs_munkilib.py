#!/usr/local/autopkg/python

import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from autopkglib import ProcessorError
from autopkglib.munkirepolibs.MunkiLib import MunkiLib


class TestMunkiLib(unittest.TestCase):
    def _library(self):
        library = MunkiLib.__new__(MunkiLib)
        library.munki_repo = "/repo"
        library.repo = MagicMock()
        return library

    def _fake_munkilib(self, content=b"plist content"):
        fake_munkilib = types.ModuleType("munkilib")
        fake_munkilib.FoundationPlist = types.SimpleNamespace(
            writePlistToString=MagicMock(return_value=content)
        )
        return fake_munkilib

    def test_put_pkginfo_to_repo_writes_relative_repo_path(self):
        library = self._library()
        fake_munkilib = self._fake_munkilib()
        pkginfo = {"name": "TestApp", "version": "1.0"}
        pkginfo_path = os.path.join("/repo", "pkgsinfo", "TestApp.plist")

        with patch.dict(sys.modules, {"munkilib": fake_munkilib}):
            library.put_pkginfo_to_repo(pkginfo, pkginfo_path)

        fake_munkilib.FoundationPlist.writePlistToString.assert_called_once_with(
            pkginfo
        )
        library.repo.put.assert_called_once_with(
            os.path.join("pkgsinfo", "TestApp.plist"), b"plist content"
        )

    def test_put_pkginfo_to_repo_wraps_repo_put_errors(self):
        library = self._library()
        library.repo.put.side_effect = RuntimeError("plugin refused write")
        fake_munkilib = self._fake_munkilib()
        pkginfo_path = os.path.join("/repo", "pkgsinfo", "TestApp.plist")

        with patch.dict(sys.modules, {"munkilib": fake_munkilib}):
            with self.assertRaises(ProcessorError) as err:
                library.put_pkginfo_to_repo({"name": "TestApp"}, pkginfo_path)

        self.assertEqual(
            str(err.exception),
            f"Could not write pkginfo {pkginfo_path}: plugin refused write",
        )
        self.assertIsInstance(err.exception.__cause__, RuntimeError)


if __name__ == "__main__":
    unittest.main()
