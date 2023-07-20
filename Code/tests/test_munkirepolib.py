#!/usr/local/autopkg/python

import copy
import imp
import os
import plistlib
import unittest
from textwrap import dedent
from unittest.mock import mock_open, patch

from autopkglib.munkirepolibs.AutoPkgLib import AutoPkgLib
from autopkglib.munkirepolibs.MunkiLib import MunkiLib

autopkg = imp.load_source(
    "autopkg", os.path.join(os.path.dirname(__file__), "..", "autopkg")
)


class TestMunkiRepoLib(unittest.TestCase):
    """Test class for munkirepolibs"""

    # Some globals for mocking
    sample_pkginfo = dedent(
        """\
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0">
        <dict>
            <key>_metadata</key>
            <dict>
                <key>created_by</key>
                <string>testuser</string>
                <key>creation_date</key>
                <date>2023-07-20T17:27:17Z</date>
                <key>munki_version</key>
                <string>6.3.1.4580</string>
                <key>os_version</key>
                <string>13.4.1</string>
            </dict>
            <key>autoremove</key>
            <false/>
            <key>catalogs</key>
            <array>
                <string>testing</string>
            </array>
            <key>description</key>
            <string>Generic description text</string>
            <key>developer</key>
            <string>Some developer</string>
            <key>display_name</key>
            <string>Generic display name</string>
            <key>installed_size</key>
            <integer>303449</integer>
            <key>installer_item_hash</key>
            <string>5d02040ebc03c836b998b1832187ecc89632a403300fa3cdde69687798e1df16</string>
            <key>installer_item_location</key>
            <string>apps/sample_item.pkg</string>
            <key>installer_item_size</key>
            <integer>181414</integer>
            <key>minimum_os_version</key>
            <string>10.5.0</string>
            <key>name</key>
            <string>AutoPkgTestItem</string>
            <key>receipts</key>
            <array>
                <dict>
                    <key>installed_size</key>
                    <integer>303449</integer>
                    <key>packageid</key>
                    <string>com.github.autopkg.testitem</string>
                    <key>version</key>
                    <string>1.0</string>
                </dict>
            </array>
            <key>supported_architectures</key>
            <array>
                <string>arm64</string>
            </array>
            <key>unattended_install</key>
            <true/>
            <key>uninstall_method</key>
            <string>removepackages</string>
            <key>uninstallable</key>
            <true/>
            <key>version</key>
            <string>1.0</string>
        </dict>
        </plist>
    """
    )
    sample_pkginfo_struct = plistlib.loads(sample_pkginfo.encode("utf-8"))

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_arch_returns_x86_64(self):
        """If supported architectures contains x86_64, return the correct arch."""
        library = AutoPkgLib("/Users/Shared/test_repo", "apps")
        test_pkginfo = copy.deepcopy(self.sample_pkginfo_struct)
        test_pkginfo["supported_architectures"] = ["x86_64"]
        arch = library.determine_arch(test_pkginfo)
        self.assertEqual(arch, "x86_64")

    def test_arch_returns_arm64(self):
        """If supported architectures contains arm64, return the correct arch."""
        library = AutoPkgLib("/Users/Shared/test_repo", "apps")
        test_pkginfo = copy.deepcopy(self.sample_pkginfo_struct)
        test_pkginfo["supported_architectures"] = ["arm64"]
        arch = library.determine_arch(test_pkginfo)
        self.assertEqual(arch, "arm64")

    def test_arch_returns_empty(self):
        """If supported architectures contains multiple entries, return empty string."""
        library = AutoPkgLib("/Users/Shared/test_repo", "apps")
        test_pkginfo = copy.deepcopy(self.sample_pkginfo_struct)
        test_pkginfo["supported_architectures"] = ["x86_64", "arm64"]
        arch = library.determine_arch(test_pkginfo)
        self.assertEqual(arch, "")

    def test_arch_is_empty_if_no_arches(self):
        """If no supported architectures specified, return empty string."""
        library = AutoPkgLib("/Users/Shared/test_repo", "apps")
        test_pkginfo = copy.deepcopy(self.sample_pkginfo_struct)
        test_pkginfo["supported_architectures"] = []
        arch = library.determine_arch(test_pkginfo)
        self.assertEqual(arch, "")
        del test_pkginfo["supported_architectures"]
        arch = library.determine_arch(test_pkginfo)
        self.assertEqual(arch, "")
