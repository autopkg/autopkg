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

from autopkglib.munkirepolibs.AutoPkgLib import AutoPkgLib


class TestAutoPkgLib(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.munki_repo = os.path.join(self.tmp_dir.name, "munki_repo")
        os.makedirs(os.path.join(self.munki_repo, "catalogs"))

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _write_all_catalog(self, items):
        with open(os.path.join(self.munki_repo, "catalogs", "all"), "wb") as f:
            plistlib.dump(items, f)

    def test_copy_pkg_to_repo_returns_full_path_for_package_already_in_repo(self):
        pkgs_subdir = os.path.join(self.munki_repo, "pkgs", "apps")
        os.makedirs(pkgs_subdir)
        pkg_path = os.path.join(pkgs_subdir, "TestApp-1.0.pkg")
        with open(pkg_path, "w") as f:
            f.write("test package")

        result = AutoPkgLib(self.munki_repo, "apps").copy_pkg_to_repo(
            {"version": "1.0"}, pkg_path
        )

        self.assertEqual(result, pkg_path)

    def test_copy_pkginfo_to_repo_strips_version_from_collision_filenames(self):
        pkginfo = {"name": "TestApp", "version": " 1.0 "}
        autopkg_lib = AutoPkgLib(self.munki_repo, "apps")

        first_result = autopkg_lib.copy_pkginfo_to_repo(pkginfo)
        second_result = autopkg_lib.copy_pkginfo_to_repo(pkginfo)

        self.assertEqual(os.path.basename(first_result), "TestApp-1.0.plist")
        self.assertEqual(os.path.basename(second_result), "TestApp-1.0__1.plist")
        with open(second_result, "rb") as f:
            saved_pkginfo = plistlib.load(f)
        self.assertEqual(saved_pkginfo["version"], " 1.0 ")

    def test_make_catalog_db_preserves_application_matches_with_same_app_version(self):
        app_path = "/Applications/TestApp.app"
        self._write_all_catalog(
            [
                {
                    "name": "TestApp",
                    "version": "1.0",
                    "installs": [
                        {
                            "type": "application",
                            "path": app_path,
                            "CFBundleShortVersionString": "100",
                        }
                    ],
                },
                {
                    "name": "TestApp",
                    "version": "1.1",
                    "installs": [
                        {
                            "type": "application",
                            "path": app_path,
                            "CFBundleShortVersionString": "100",
                        }
                    ],
                },
            ]
        )

        pkgdb = AutoPkgLib(self.munki_repo, None).make_catalog_db()

        self.assertEqual(pkgdb["applications"][app_path]["100"], [0, 1])


if __name__ == "__main__":
    unittest.main()
