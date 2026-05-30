#!/usr/local/autopkg/python

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
