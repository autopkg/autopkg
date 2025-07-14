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

import imp
import os
import sys
import unittest

# Add the Code directory to the Python path to resolve autopkg dependencies
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

autopkg = imp.load_source(
    "autopkg", os.path.join(os.path.dirname(__file__), "..", "autopkg")
)


class TestAutoPkgRecipes(unittest.TestCase):
    """Test cases for recipe-related functions of AutoPkg."""

    def setUp(self):
        if autopkg is None:
            self.skipTest("autopkg module could not be imported")

    def test_recipe_has_step_processor_with_processor(self):
        """Test recipe_has_step_processor when recipe contains the specified processor."""
        recipe = {
            "Process": [
                {"Processor": "URLDownloader"},
                {"Processor": "CodeSignatureVerifier"},
                {"Processor": "MunkiImporter"},
            ]
        }

        result = autopkg.recipe_has_step_processor(recipe, "MunkiImporter")
        self.assertTrue(result)

        result = autopkg.recipe_has_step_processor(recipe, "URLDownloader")
        self.assertTrue(result)

        result = autopkg.recipe_has_step_processor(recipe, "CodeSignatureVerifier")
        self.assertTrue(result)

    def test_recipe_has_step_processor_without_processor(self):
        """Test recipe_has_step_processor when recipe does not contain the specified processor."""
        recipe = {
            "Process": [
                {"Processor": "URLDownloader"},
                {"Processor": "CodeSignatureVerifier"},
            ]
        }

        result = autopkg.recipe_has_step_processor(recipe, "MunkiImporter")
        self.assertFalse(result)

        result = autopkg.recipe_has_step_processor(recipe, "PkgCreator")
        self.assertFalse(result)

    def test_recipe_has_step_processor_no_process_key(self):
        """Test recipe_has_step_processor when recipe has no Process key."""
        recipe = {
            "Input": {"NAME": "TestApp"},
            "Description": "Test recipe without Process key",
        }

        result = autopkg.recipe_has_step_processor(recipe, "MunkiImporter")
        self.assertFalse(result)

    def test_recipe_has_step_processor_empty_process(self):
        """Test recipe_has_step_processor when Process list is empty."""
        recipe = {"Process": []}

        result = autopkg.recipe_has_step_processor(recipe, "MunkiImporter")
        self.assertFalse(result)

    def test_recipe_has_step_processor_none_process(self):
        """Test recipe_has_step_processor when Process is None raises TypeError."""
        recipe = {"Process": None}

        # The function should raise TypeError when trying to iterate over None
        with self.assertRaises(TypeError):
            autopkg.recipe_has_step_processor(recipe, "MunkiImporter")

    def test_recipe_has_step_processor_steps_without_processor_key(self):
        """Test recipe_has_step_processor when steps don't have Processor key."""
        recipe = {
            "Process": [
                {"Arguments": {"some_arg": "value"}},
                {"Processor": "URLDownloader"},
                {"Comment": "This step has no Processor key"},
            ]
        }

        result = autopkg.recipe_has_step_processor(recipe, "URLDownloader")
        self.assertTrue(result)

        result = autopkg.recipe_has_step_processor(recipe, "MunkiImporter")
        self.assertFalse(result)

    def test_recipe_has_step_processor_case_sensitive(self):
        """Test recipe_has_step_processor is case sensitive."""
        recipe = {
            "Process": [
                {"Processor": "MunkiImporter"},
            ]
        }

        result = autopkg.recipe_has_step_processor(recipe, "MunkiImporter")
        self.assertTrue(result)

        result = autopkg.recipe_has_step_processor(recipe, "munkiimporter")
        self.assertFalse(result)

        result = autopkg.recipe_has_step_processor(recipe, "MUNKIIMPORTER")
        self.assertFalse(result)

    def test_recipe_has_step_processor_multiple_same_processor(self):
        """Test recipe_has_step_processor when same processor appears multiple times."""
        recipe = {
            "Process": [
                {"Processor": "URLDownloader"},
                {"Processor": "MunkiImporter"},
                {"Processor": "URLDownloader"},  # Same processor again
            ]
        }

        result = autopkg.recipe_has_step_processor(recipe, "URLDownloader")
        self.assertTrue(result)

        result = autopkg.recipe_has_step_processor(recipe, "MunkiImporter")
        self.assertTrue(result)

    def test_recipe_has_step_processor_with_shared_processor(self):
        """Test recipe_has_step_processor with shared processor syntax."""
        recipe = {
            "Process": [
                {"Processor": "com.github.autopkg.shared/SharedProcessor"},
                {"Processor": "URLDownloader"},
            ]
        }

        result = autopkg.recipe_has_step_processor(
            recipe, "com.github.autopkg.shared/SharedProcessor"
        )
        self.assertTrue(result)

        result = autopkg.recipe_has_step_processor(recipe, "SharedProcessor")
        self.assertFalse(result)

    def test_recipe_has_step_processor_empty_processor_name(self):
        """Test recipe_has_step_processor with empty processor name."""
        recipe = {
            "Process": [
                {"Processor": "URLDownloader"},
                {"Processor": ""},  # Empty processor name
            ]
        }

        result = autopkg.recipe_has_step_processor(recipe, "")
        self.assertTrue(result)

        result = autopkg.recipe_has_step_processor(recipe, "URLDownloader")
        self.assertTrue(result)

    def test_recipe_has_step_processor_none_processor_value(self):
        """Test recipe_has_step_processor when Processor value is None."""
        recipe = {
            "Process": [
                {"Processor": "URLDownloader"},
                {"Processor": None},  # None processor value
            ]
        }

        result = autopkg.recipe_has_step_processor(recipe, None)
        self.assertTrue(result)

        result = autopkg.recipe_has_step_processor(recipe, "URLDownloader")
        self.assertTrue(result)

    def test_has_munkiimporter_step_with_munkiimporter(self):
        """Test has_munkiimporter_step when recipe contains MunkiImporter."""
        recipe = {
            "Process": [
                {"Processor": "URLDownloader"},
                {"Processor": "MunkiImporter"},
                {"Processor": "CodeSignatureVerifier"},
            ]
        }

        result = autopkg.has_munkiimporter_step(recipe)
        self.assertTrue(result)

    def test_has_munkiimporter_step_without_munkiimporter(self):
        """Test has_munkiimporter_step when recipe does not contain MunkiImporter."""
        recipe = {
            "Process": [
                {"Processor": "URLDownloader"},
                {"Processor": "CodeSignatureVerifier"},
                {"Processor": "PkgCreator"},
            ]
        }

        result = autopkg.has_munkiimporter_step(recipe)
        self.assertFalse(result)

    def test_has_munkiimporter_step_no_process_key(self):
        """Test has_munkiimporter_step when recipe has no Process key."""
        recipe = {
            "Input": {"NAME": "TestApp"},
            "Description": "Test recipe without Process key",
        }

        result = autopkg.has_munkiimporter_step(recipe)
        self.assertFalse(result)

    def test_has_munkiimporter_step_empty_process(self):
        """Test has_munkiimporter_step when Process list is empty."""
        recipe = {"Process": []}

        result = autopkg.has_munkiimporter_step(recipe)
        self.assertFalse(result)

    def test_has_munkiimporter_step_none_process(self):
        """Test has_munkiimporter_step when Process is None raises TypeError."""
        recipe = {"Process": None}

        # The function should raise TypeError when trying to iterate over None
        with self.assertRaises(TypeError):
            autopkg.has_munkiimporter_step(recipe)

    def test_has_munkiimporter_step_case_sensitive(self):
        """Test has_munkiimporter_step is case sensitive."""
        recipe = {
            "Process": [
                {"Processor": "munkiimporter"},  # lowercase
                {"Processor": "MUNKIIMPORTER"},  # uppercase
            ]
        }

        # Should be False because it looks specifically for "MunkiImporter"
        result = autopkg.has_munkiimporter_step(recipe)
        self.assertFalse(result)

        # Test with correct case
        recipe_correct = {
            "Process": [
                {"Processor": "MunkiImporter"},
            ]
        }

        result = autopkg.has_munkiimporter_step(recipe_correct)
        self.assertTrue(result)

    def test_has_munkiimporter_step_multiple_munkiimporter(self):
        """Test has_munkiimporter_step when MunkiImporter appears multiple times."""
        recipe = {
            "Process": [
                {"Processor": "URLDownloader"},
                {"Processor": "MunkiImporter"},
                {"Processor": "CodeSignatureVerifier"},
                {"Processor": "MunkiImporter"},  # MunkiImporter again
            ]
        }

        result = autopkg.has_munkiimporter_step(recipe)
        self.assertTrue(result)

    def test_has_munkiimporter_step_with_shared_processor(self):
        """Test has_munkiimporter_step with shared processor syntax."""
        recipe = {
            "Process": [
                {"Processor": "com.github.autopkg.shared/MunkiImporter"},
                {"Processor": "URLDownloader"},
            ]
        }

        # Should be False because it looks specifically for "MunkiImporter", not the shared version
        result = autopkg.has_munkiimporter_step(recipe)
        self.assertFalse(result)

        # Test with exact match
        recipe_exact = {
            "Process": [
                {"Processor": "MunkiImporter"},
            ]
        }

        result = autopkg.has_munkiimporter_step(recipe_exact)
        self.assertTrue(result)

    def test_has_munkiimporter_step_steps_without_processor_key(self):
        """Test has_munkiimporter_step when some steps don't have Processor key."""
        recipe = {
            "Process": [
                {"Arguments": {"some_arg": "value"}},  # No Processor key
                {"Processor": "URLDownloader"},
                {"Comment": "This step has no Processor key"},  # No Processor key
                {"Processor": "MunkiImporter"},
            ]
        }

        result = autopkg.has_munkiimporter_step(recipe)
        self.assertTrue(result)

    def test_has_munkiimporter_step_empty_recipe_dict(self):
        """Test has_munkiimporter_step with empty recipe dictionary."""
        recipe = {}

        result = autopkg.has_munkiimporter_step(recipe)
        self.assertFalse(result)

    def test_has_munkiimporter_step_real_world_recipe(self):
        """Test has_munkiimporter_step with a realistic recipe structure."""
        recipe = {
            "Description": "Downloads and imports Firefox into Munki",
            "Identifier": "com.github.autopkg.munki.firefox",
            "Input": {
                "NAME": "Firefox",
                "MUNKI_REPO_SUBDIR": "apps/mozilla",
            },
            "MinimumVersion": "1.0.0",
            "Process": [
                {
                    "Processor": "MozillaURLProvider",
                    "Arguments": {"product_name": "firefox", "release": "latest"},
                },
                {
                    "Processor": "URLDownloader",
                    "Arguments": {"filename": "%NAME%.dmg"},
                },
                {
                    "Processor": "EndOfCheckPhase",
                },
                {
                    "Processor": "CodeSignatureVerifier",
                    "Arguments": {
                        "input_path": "%pathname%/Firefox.app",
                        "requirement": 'identifier "org.mozilla.firefox"',
                    },
                },
                {
                    "Processor": "MunkiImporter",
                    "Arguments": {
                        "pkg_path": "%pathname%",
                        "repo_subdirectory": "%MUNKI_REPO_SUBDIR%",
                    },
                },
            ],
        }

        result = autopkg.has_munkiimporter_step(recipe)
        self.assertTrue(result)

        # Test a recipe without MunkiImporter
        recipe_without_munki = {
            "Description": "Downloads Firefox",
            "Identifier": "com.github.autopkg.download.firefox",
            "Process": [
                {
                    "Processor": "MozillaURLProvider",
                    "Arguments": {"product_name": "firefox", "release": "latest"},
                },
                {
                    "Processor": "URLDownloader",
                    "Arguments": {"filename": "%NAME%.dmg"},
                },
                {
                    "Processor": "EndOfCheckPhase",
                },
            ],
        }

        result = autopkg.has_munkiimporter_step(recipe_without_munki)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
