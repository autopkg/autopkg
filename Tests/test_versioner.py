#!/usr/bin/python
#
# Copyright 2015 Shea G. Craig
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
import unittest
import sys

sys.path.append(os.path.join(os.getcwd(), "..", "Code"))
import autopkglib
import FoundationPlist


class TestVersioner(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        resources = os.path.join(os.getcwd(), "resources")
        # TODO: Replace all of these files with a mock.
        cls.test_app_name = "Test.app"
        cls.test_empty_app_name = "TestEmpty.app"
        cls.test_plugin_name = "Test.plugin"
        cls.test_empty_bundle = os.path.join(resources, "EmptyInfo.plist")
        cls.test_empty_app = os.path.join(resources, cls.test_empty_app_name)
        cls.test_app = os.path.join(resources, cls.test_app_name)
        cls.test_dmg = os.path.join(resources, "Test.dmg")
        cls.test_dmg_multiple = os.path.join(resources, "TestMultiple.dmg")
        cls.test_dmg_no_app = os.path.join(resources, "TestNoApp.dmg")
        cls.expected = FoundationPlist.readPlist(os.path.join(
            cls.test_app, "Contents/Info.plist"))

    def setUp(self):
        self.env = {}

    def test_as_appdmgversioner_replacement(self):
        # AppDmgVersioner accepts one input argument: dmg_path.
        # As per conversation in
        # https://github.com/autopkg/autopkg/pull/236, deprecating
        # AppDmgVersioner will mean switching to using Versioner's
        # input argument name of "input_plist_path".
        # Therefore, this tests for whether giving a disk image as input
        # results in a version, app_name (first app found within the
        # bundle-other tests confirm the searching behavior), and
        # bundleid being returned.
        results = self.process(self.test_dmg)
        versioner = autopkglib.Versioner(data=self.env)
        results = versioner.process()

        # AppDmgVersioner _only_ uses ShortVersionString
        self.assertEqual(
            results["version"], self.expected["CFBundleShortVersionString"])
        self.assertEqual(results["app_name"], self.test_app_name)
        self.assertEqual(
            results["bundleid"], self.expected["CFBundleIdentifier"])

    def test_get_shortversionstring(self):
        results = self.process(self.test_app)
        self.assertEqual(
            results["version"], self.expected["CFBundleShortVersionString"])

    def test_get_cfbundleversion(self):
        cfbundleversion = "CFBundleVersion"
        results = self.process(self.test_app, cfbundleversion)
        self.assertEqual(results["version"], self.expected[cfbundleversion])
        results = self.process(self.test_empty_app)
        self.assertEqual(results["version"], "UNKNOWN_VERSION")

    def test_get_bundle_id(self):
        results = self.process(self.test_app)
        self.assertEqual(
            results["bundleid"], self.expected["CFBundleIdentifier"])
        results = self.process(self.test_empty_app)
        self.assertEqual(results["bundleid"], "UNKNOWN_BUNDLE_ID")

    def test_get_app_name(self):
        # Test with an app as input
        results = self.process(self.test_app)
        self.assertEqual(results["app_name"], self.test_app_name)

        # Test with a dmg as input
        results = self.process(self.test_dmg)
        self.assertEqual(results["app_name"], self.test_app_name)

        # Test with a full path to plist as input
        results = self.process(
            os.path.join(self.test_app, "Contents/Info.plist"))
        self.assertEqual(results["app_name"], self.test_app_name)

        # Test with a full path to a plist in a dmg as input
        results = self.process(
            os.path.join(self.test_dmg, "Contents/Info.plist"))
        self.assertEqual(results["app_name"], self.test_app_name)

        # Test that no bundle results in exception.
        self.assertRaises(autopkglib.ProcessorError, self.process,
                          self.test_empty_bundle)

    def test_find_app_in_dmg_with_others(self):
        results = self.process(self.test_dmg_multiple)
        self.assertEqual(
            results["app_name"], self.test_app_name)

    def test_find_plugin_in_dmg_with_others(self):
        results = self.process(self.test_dmg_no_app)
        self.assertEqual(
            results["app_name"], self.test_plugin_name)

    def process(self, input_plist_path, plist_version_key=None):
        self.env["input_plist_path"] = input_plist_path
        if plist_version_key:
            self.env["plist_version_key"] = plist_version_key
        # Versioner subclasses DMGMounter, which renames the env
        # parameter to "data".
        versioner = autopkglib.Versioner(data=self.env)
        return versioner.process()

if __name__ == "__main__":
    unittest.main()
