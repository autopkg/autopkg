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
