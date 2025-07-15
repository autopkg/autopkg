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
from unittest.mock import Mock, patch

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

    def test_has_check_phase_with_endofcheckphase(self):
        """Test has_check_phase when recipe contains EndOfCheckPhase."""
        recipe = {
            "Process": [
                {"Processor": "URLDownloader"},
                {"Processor": "EndOfCheckPhase"},
                {"Processor": "CodeSignatureVerifier"},
            ]
        }

        result = autopkg.has_check_phase(recipe)
        self.assertTrue(result)

    def test_has_check_phase_without_endofcheckphase(self):
        """Test has_check_phase when recipe does not contain EndOfCheckPhase."""
        recipe = {
            "Process": [
                {"Processor": "URLDownloader"},
                {"Processor": "CodeSignatureVerifier"},
                {"Processor": "MunkiImporter"},
            ]
        }

        result = autopkg.has_check_phase(recipe)
        self.assertFalse(result)

    def test_has_check_phase_no_process_key(self):
        """Test has_check_phase when recipe has no Process key."""
        recipe = {
            "Input": {"NAME": "TestApp"},
            "Description": "Test recipe without Process key",
        }

        result = autopkg.has_check_phase(recipe)
        self.assertFalse(result)

    def test_has_check_phase_empty_process(self):
        """Test has_check_phase when Process list is empty."""
        recipe = {"Process": []}

        result = autopkg.has_check_phase(recipe)
        self.assertFalse(result)

    def test_builds_a_package_with_pkgcreator(self):
        """Test builds_a_package when recipe contains PkgCreator."""
        recipe = {
            "Process": [
                {"Processor": "URLDownloader"},
                {"Processor": "PkgCreator"},
                {"Processor": "MunkiImporter"},
            ]
        }

        result = autopkg.builds_a_package(recipe)
        self.assertTrue(result)

    def test_builds_a_package_without_pkgcreator(self):
        """Test builds_a_package when recipe does not contain PkgCreator."""
        recipe = {
            "Process": [
                {"Processor": "URLDownloader"},
                {"Processor": "CodeSignatureVerifier"},
                {"Processor": "MunkiImporter"},
            ]
        }

        result = autopkg.builds_a_package(recipe)
        self.assertFalse(result)

    def test_builds_a_package_no_process_key(self):
        """Test builds_a_package when recipe has no Process key."""
        recipe = {
            "Input": {"NAME": "TestApp"},
            "Description": "Test recipe without Process key",
        }

        result = autopkg.builds_a_package(recipe)
        self.assertFalse(result)

    def test_builds_a_package_empty_process(self):
        """Test builds_a_package when Process list is empty."""
        recipe = {"Process": []}

        result = autopkg.builds_a_package(recipe)
        self.assertFalse(result)

    def test_valid_recipe_dict_with_keys_valid_dict(self):
        """Test valid_recipe_dict_with_keys with a valid dictionary containing all required keys."""
        recipe_dict = {
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
            "Description": "Test recipe",
        }
        keys_to_verify = ["Input", "Process"]

        result = autopkg.valid_recipe_dict_with_keys(recipe_dict, keys_to_verify)
        self.assertTrue(result)

    def test_valid_recipe_dict_with_keys_missing_key(self):
        """Test valid_recipe_dict_with_keys with dictionary missing a required key."""
        recipe_dict = {
            "Input": {"NAME": "TestApp"},
            "Description": "Test recipe without Process key",
        }
        keys_to_verify = ["Input", "Process"]

        result = autopkg.valid_recipe_dict_with_keys(recipe_dict, keys_to_verify)
        self.assertFalse(result)

    def test_valid_recipe_dict_with_keys_empty_dict(self):
        """Test valid_recipe_dict_with_keys with empty dictionary."""
        recipe_dict = {}
        keys_to_verify = ["Input", "Process"]

        result = autopkg.valid_recipe_dict_with_keys(recipe_dict, keys_to_verify)
        self.assertFalse(result)

    def test_valid_recipe_dict_with_keys_none_dict(self):
        """Test valid_recipe_dict_with_keys with None dictionary."""
        recipe_dict = None
        keys_to_verify = ["Input", "Process"]

        result = autopkg.valid_recipe_dict_with_keys(recipe_dict, keys_to_verify)
        self.assertFalse(result)

    def test_valid_recipe_dict_with_keys_empty_keys_list(self):
        """Test valid_recipe_dict_with_keys with empty keys list."""
        recipe_dict = {
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }
        keys_to_verify = []

        result = autopkg.valid_recipe_dict_with_keys(recipe_dict, keys_to_verify)
        self.assertTrue(result)

    def test_valid_recipe_dict_with_keys_extra_keys(self):
        """Test valid_recipe_dict_with_keys with dictionary containing extra keys beyond required."""
        recipe_dict = {
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "MinimumVersion": "1.0.0",
        }
        keys_to_verify = ["Input", "Process"]

        result = autopkg.valid_recipe_dict_with_keys(recipe_dict, keys_to_verify)
        self.assertTrue(result)

    def test_valid_recipe_dict_input_process(self):
        """Test valid_recipe_dict with Identifier, Input and Process keys (standard recipe)."""
        recipe_dict = {
            "Identifier": "com.example.test.download",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        result = autopkg.valid_recipe_dict(recipe_dict)
        self.assertTrue(result)

    def test_valid_recipe_dict_input_parentrecipe(self):
        """Test valid_recipe_dict with Identifier, Input and ParentRecipe keys (override)."""
        recipe_dict = {
            "Identifier": "com.example.test.override",
            "Input": {"NAME": "TestApp"},
            "ParentRecipe": "com.example.parent.download",
        }

        result = autopkg.valid_recipe_dict(recipe_dict)
        self.assertTrue(result)

    def test_valid_recipe_dict_invalid_missing_input(self):
        """Test valid_recipe_dict with missing Input key."""
        recipe_dict = {
            "Identifier": "com.example.test.download",
            "Process": [{"Processor": "URLDownloader"}],
        }

        result = autopkg.valid_recipe_dict(recipe_dict)
        self.assertFalse(result)

    def test_valid_recipe_dict_invalid_missing_process_recipe_parent(self):
        """Test valid_recipe_dict with Identifier and Input but missing Process and ParentRecipe."""
        recipe_dict = {
            "Identifier": "com.example.test.invalid",
            "Input": {"NAME": "TestApp"},
            "Description": "Test recipe without required second key",
        }

        result = autopkg.valid_recipe_dict(recipe_dict)
        self.assertFalse(result)

    def test_valid_recipe_dict_empty_dict(self):
        """Test valid_recipe_dict with empty dictionary."""
        recipe_dict = {}

        result = autopkg.valid_recipe_dict(recipe_dict)
        self.assertFalse(result)

    def test_valid_recipe_dict_none(self):
        """Test valid_recipe_dict with None."""
        recipe_dict = None

        result = autopkg.valid_recipe_dict(recipe_dict)
        self.assertFalse(result)

    def test_valid_recipe_dict_complete_recipe(self):
        """Test valid_recipe_dict with a complete realistic recipe."""
        recipe_dict = {
            "Description": "Downloads Firefox",
            "Identifier": "com.github.autopkg.download.firefox",
            "Input": {
                "NAME": "Firefox",
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
            ],
        }

        result = autopkg.valid_recipe_dict(recipe_dict)
        self.assertTrue(result)

    def test_valid_override_dict_input_parentrecipe(self):
        """Test valid_override_dict with Identifier, Input, and ParentRecipe keys."""
        override_dict = {
            "Identifier": "com.example.test.override",
            "Input": {"NAME": "CustomFirefox"},
            "ParentRecipe": "com.github.autopkg.download.firefox",
        }

        result = autopkg.valid_override_dict(override_dict)
        self.assertTrue(result)

    def test_valid_override_dict_with_optional_parent_recipe_trust_info(self):
        """Test valid_override_dict with optional ParentRecipeTrustInfo key."""
        override_dict = {
            "Identifier": "com.example.test.override",
            "Input": {"NAME": "CustomFirefox"},
            "ParentRecipe": "com.github.autopkg.download.firefox",
            "ParentRecipeTrustInfo": {
                "non_core_processors": {},
                "parent_recipes": {
                    "com.github.autopkg.download.firefox": {
                        "git_hash": "abc123def456",
                        "path": "/path/to/recipe",
                        "sha256_hash": "def456abc123",
                    }
                },
            },
        }

        result = autopkg.valid_override_dict(override_dict)
        self.assertTrue(result)

    def test_valid_override_dict_invalid_missing_input(self):
        """Test valid_override_dict with missing Input key."""
        override_dict = {
            "Identifier": "com.example.test.override",
            "ParentRecipe": "com.github.autopkg.download.firefox",
        }

        result = autopkg.valid_override_dict(override_dict)
        self.assertFalse(result)

    def test_valid_override_dict_empty_dict(self):
        """Test valid_override_dict with empty dictionary."""
        override_dict = {}

        result = autopkg.valid_override_dict(override_dict)
        self.assertFalse(result)

    def test_valid_override_dict_none(self):
        """Test valid_override_dict with None."""
        override_dict = None

        result = autopkg.valid_override_dict(override_dict)
        self.assertFalse(result)

    def test_valid_override_dict_complete_override(self):
        """Test valid_override_dict with a complete realistic override."""
        override_dict = {
            "Description": "Custom Firefox override for my organization",
            "Identifier": "com.myorg.autopkg.munki.firefox",
            "Input": {
                "NAME": "Firefox",
                "MUNKI_REPO_SUBDIR": "apps/mozilla",
                "pkginfo": {
                    "catalogs": ["testing"],
                    "category": "Internet",
                    "description": "Mozilla Firefox web browser",
                },
            },
            "ParentRecipe": "com.github.autopkg.munki.firefox",
            "ParentRecipeTrustInfo": {
                "non_core_processors": {},
                "parent_recipes": {
                    "com.github.autopkg.munki.firefox": {
                        "git_hash": "abc123def456789",
                        "path": "/Users/example/Library/AutoPkg/RecipeRepos/recipes/Firefox/Firefox.munki.recipe",
                        "sha256_hash": "def456abc123789",
                    }
                },
            },
        }

        result = autopkg.valid_override_dict(override_dict)
        self.assertTrue(result)

    def test_valid_recipe_file_valid_file(self):
        """Test valid_recipe_file with a valid recipe file."""
        # Create a temporary recipe file
        import plistlib
        import tempfile

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".recipe", delete=False
        ) as f:
            plistlib.dump(recipe_dict, f)
            temp_file = f.name

        try:
            result = autopkg.valid_recipe_file(temp_file)
            self.assertTrue(result)
        finally:
            os.unlink(temp_file)

    def test_valid_recipe_file_invalid_file(self):
        """Test valid_recipe_file with an invalid recipe file."""
        import plistlib
        import tempfile

        # Create a recipe without required keys (missing Identifier and Input)
        recipe_dict = {
            "Description": "Invalid recipe",
            "Process": [{"Processor": "URLDownloader"}],
        }

        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".recipe", delete=False
        ) as f:
            plistlib.dump(recipe_dict, f)
            temp_file = f.name

        try:
            result = autopkg.valid_recipe_file(temp_file)
            self.assertFalse(result)
        finally:
            os.unlink(temp_file)

    def test_valid_recipe_file_nonexistent_file(self):
        """Test valid_recipe_file with nonexistent file."""
        result = autopkg.valid_recipe_file("/nonexistent/path/to/recipe.recipe")
        self.assertFalse(result)

    def test_valid_recipe_file_malformed_plist(self):
        """Test valid_recipe_file with malformed plist file."""
        import tempfile

        # Create a malformed plist file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".recipe", delete=False) as f:
            f.write("This is not a valid plist file")
            temp_file = f.name

        try:
            result = autopkg.valid_recipe_file(temp_file)
            self.assertFalse(result)
        finally:
            os.unlink(temp_file)

    def test_valid_override_file_valid_file(self):
        """Test valid_override_file with a valid override file."""
        import plistlib
        import tempfile

        override_dict = {
            "Description": "Test override",
            "Identifier": "com.example.test.override",
            "Input": {"NAME": "TestApp"},
            "ParentRecipe": "com.example.test.download",
        }

        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".recipe", delete=False
        ) as f:
            plistlib.dump(override_dict, f)
            temp_file = f.name

        try:
            result = autopkg.valid_override_file(temp_file)
            self.assertTrue(result)
        finally:
            os.unlink(temp_file)

    def test_valid_override_file_invalid_file(self):
        """Test valid_override_file with an invalid override file."""
        import plistlib
        import tempfile

        # Create an override without required keys (missing Identifier and Input)
        override_dict = {
            "Description": "Invalid override",
            "ParentRecipe": "com.example.test.download",
        }

        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".recipe", delete=False
        ) as f:
            plistlib.dump(override_dict, f)
            temp_file = f.name

        try:
            result = autopkg.valid_override_file(temp_file)
            self.assertFalse(result)
        finally:
            os.unlink(temp_file)

    def test_valid_override_file_nonexistent_file(self):
        """Test valid_override_file with nonexistent file."""
        result = autopkg.valid_override_file("/nonexistent/path/to/override.recipe")
        self.assertFalse(result)

    def test_valid_override_file_malformed_plist(self):
        """Test valid_override_file with malformed plist file."""
        import tempfile

        # Create a malformed plist file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".recipe", delete=False) as f:
            f.write("This is not a valid plist file")
            temp_file = f.name

        try:
            result = autopkg.valid_override_file(temp_file)
            self.assertFalse(result)
        finally:
            os.unlink(temp_file)

    def test_valid_recipe_dict_with_keys_partial_match(self):
        """Test valid_recipe_dict_with_keys when only some keys are present."""
        recipe_dict = {
            "Input": {"NAME": "TestApp"},
            "Identifier": "com.example.test",
        }
        keys_to_verify = ["Input", "Process", "Description"]

        result = autopkg.valid_recipe_dict_with_keys(recipe_dict, keys_to_verify)
        self.assertFalse(result)

    def test_find_recipe_by_name_with_valid_recipe(self):
        """Test find_recipe_by_name when a valid recipe file exists."""
        import plistlib
        import tempfile

        # Create a temporary recipe file
        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.testapp.download",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        # Create a temporary directory and recipe file
        with tempfile.TemporaryDirectory() as temp_dir:
            recipe_file = os.path.join(temp_dir, "TestApp.download.recipe")
            with open(recipe_file, "wb") as f:
                plistlib.dump(recipe_dict, f)

            result = autopkg.find_recipe_by_name("TestApp.download", [temp_dir])
            self.assertEqual(result, recipe_file)

    def test_find_recipe_by_name_without_extension(self):
        """Test find_recipe_by_name when recipe name is provided without extension."""
        import plistlib
        import tempfile

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.testapp.download",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            recipe_file = os.path.join(temp_dir, "TestApp.download.recipe")
            with open(recipe_file, "wb") as f:
                plistlib.dump(recipe_dict, f)

            # Should find recipe even without .recipe extension
            result = autopkg.find_recipe_by_name("TestApp.download", [temp_dir])
            self.assertEqual(result, recipe_file)

    def test_find_recipe_by_name_in_subdirectory(self):
        """Test find_recipe_by_name when recipe is in a subdirectory."""
        import plistlib
        import tempfile

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.testapp.download",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            subdir = os.path.join(temp_dir, "apps")
            os.makedirs(subdir)
            recipe_file = os.path.join(subdir, "TestApp.download.recipe")
            with open(recipe_file, "wb") as f:
                plistlib.dump(recipe_dict, f)

            result = autopkg.find_recipe_by_name("TestApp.download", [temp_dir])
            self.assertEqual(result, recipe_file)

    def test_find_recipe_by_name_nonexistent_recipe(self):
        """Test find_recipe_by_name when recipe doesn't exist."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            result = autopkg.find_recipe_by_name("NonExistent.download", [temp_dir])
            self.assertIsNone(result)

    def test_find_recipe_by_name_invalid_recipe(self):
        """Test find_recipe_by_name when recipe file exists but is invalid."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create an invalid recipe file (missing required keys)
            invalid_recipe_file = os.path.join(temp_dir, "Invalid.download.recipe")
            with open(invalid_recipe_file, "w") as f:
                f.write("This is not a valid plist")

            result = autopkg.find_recipe_by_name("Invalid.download", [temp_dir])
            self.assertIsNone(result)

    def test_find_recipe_by_name_empty_search_dirs(self):
        """Test find_recipe_by_name with empty search directories."""
        result = autopkg.find_recipe_by_name("TestApp.download", [])
        self.assertIsNone(result)

    def test_find_recipe_by_name_nonexistent_search_dir(self):
        """Test find_recipe_by_name with nonexistent search directory."""
        result = autopkg.find_recipe_by_name("TestApp.download", ["/nonexistent/path"])
        self.assertIsNone(result)

    def test_find_recipe_finds_by_identifier(self):
        """Test find_recipe when recipe can be found by identifier."""
        import plistlib
        import tempfile

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.testapp.download",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            recipe_file = os.path.join(temp_dir, "TestApp.download.recipe")
            with open(recipe_file, "wb") as f:
                plistlib.dump(recipe_dict, f)

            # Mock find_recipe_by_identifier to return our test file
            original_find_by_id = autopkg.find_recipe_by_identifier
            autopkg.find_recipe_by_identifier = lambda id_name, dirs: (
                recipe_file if id_name == "com.example.testapp.download" else None
            )

            try:
                result = autopkg.find_recipe("com.example.testapp.download", [temp_dir])
                self.assertEqual(result, recipe_file)
            finally:
                autopkg.find_recipe_by_identifier = original_find_by_id

    def test_find_recipe_finds_by_name(self):
        """Test find_recipe when recipe can be found by name but not identifier."""
        import plistlib
        import tempfile

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.testapp.download",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            recipe_file = os.path.join(temp_dir, "TestApp.download.recipe")
            with open(recipe_file, "wb") as f:
                plistlib.dump(recipe_dict, f)

            # Mock find_recipe_by_identifier to return None
            original_find_by_id = autopkg.find_recipe_by_identifier
            autopkg.find_recipe_by_identifier = lambda id_name, dirs: None

            try:
                result = autopkg.find_recipe("TestApp.download", [temp_dir])
                self.assertEqual(result, recipe_file)
            finally:
                autopkg.find_recipe_by_identifier = original_find_by_id

    def test_find_recipe_not_found(self):
        """Test find_recipe when recipe cannot be found by identifier or name."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock find_recipe_by_identifier to return None
            original_find_by_id = autopkg.find_recipe_by_identifier
            autopkg.find_recipe_by_identifier = lambda id_name, dirs: None

            try:
                result = autopkg.find_recipe("NonExistent.download", [temp_dir])
                self.assertIsNone(result)
            finally:
                autopkg.find_recipe_by_identifier = original_find_by_id

    def test_get_identifier_from_override_with_parent_recipe(self):
        """Test get_identifier_from_override when override has ParentRecipe key."""
        override = {
            "Identifier": "com.example.testapp.override",
            "Input": {"NAME": "TestApp"},
            "ParentRecipe": "com.example.testapp.download",
        }

        result = autopkg.get_identifier_from_override(override)
        self.assertEqual(result, "com.example.testapp.download")

    def test_get_identifier_from_override_with_recipe_identifier(self):
        """Test get_identifier_from_override when override has Recipe with identifier."""
        override = {
            "Identifier": "com.example.testapp.override",
            "Input": {"NAME": "TestApp"},
            "Recipe": {"identifier": "com.example.testapp.download"},
        }

        result = autopkg.get_identifier_from_override(override)
        self.assertEqual(result, "com.example.testapp.download")

    def test_get_identifier_from_override_with_recipe_name_fallback(self):
        """Test get_identifier_from_override when override falls back to Recipe name."""
        override = {
            "Identifier": "com.example.testapp.override",
            "Input": {"NAME": "TestApp"},
            "Recipe": {"name": "TestApp.download"},
        }

        # Capture log_err calls to verify warning is logged
        original_log_err = autopkg.log_err
        logged_messages = []
        autopkg.log_err = lambda msg: logged_messages.append(msg)

        try:
            result = autopkg.get_identifier_from_override(override)
            self.assertEqual(result, "TestApp.download")
            self.assertTrue(
                any(
                    "WARNING: Override contains no identifier" in msg
                    for msg in logged_messages
                )
            )
        finally:
            autopkg.log_err = original_log_err

    def test_get_identifier_from_override_prefers_parent_recipe(self):
        """Test get_identifier_from_override prefers ParentRecipe over Recipe identifier."""
        override = {
            "Identifier": "com.example.testapp.override",
            "Input": {"NAME": "TestApp"},
            "ParentRecipe": "com.example.testapp.parent",
            "Recipe": {"identifier": "com.example.testapp.download"},
        }

        result = autopkg.get_identifier_from_override(override)
        self.assertEqual(result, "com.example.testapp.parent")

    def test_get_identifier_from_override_no_parent_recipe(self):
        """Test get_identifier_from_override when override has no ParentRecipe."""
        override = {
            "Identifier": "com.example.testapp.override",
            "Input": {"NAME": "TestApp"},
            "Recipe": {"identifier": "com.example.testapp.download"},
        }

        result = autopkg.get_identifier_from_override(override)
        self.assertEqual(result, "com.example.testapp.download")

    def test_get_identifier_from_override_empty_parent_recipe(self):
        """Test get_identifier_from_override when ParentRecipe is empty."""
        override = {
            "Identifier": "com.example.testapp.override",
            "Input": {"NAME": "TestApp"},
            "ParentRecipe": "",
            "Recipe": {"identifier": "com.example.testapp.download"},
        }

        result = autopkg.get_identifier_from_override(override)
        self.assertEqual(result, "com.example.testapp.download")

    # Tests for locate_recipe function
    def test_locate_recipe_file_path(self):
        """Test locate_recipe when given a direct file path."""
        import plistlib
        import tempfile

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".recipe", delete=False
        ) as f:
            plistlib.dump(recipe_dict, f)
            temp_file = f.name

        try:
            result = autopkg.locate_recipe(
                temp_file, [], [], make_suggestions=False, search_github=False
            )
            self.assertEqual(result, temp_file)
        finally:
            os.unlink(temp_file)

    def test_locate_recipe_invalid_file_path(self):
        """Test locate_recipe with an invalid file path."""
        invalid_file = "/nonexistent/path/recipe.recipe"
        result = autopkg.locate_recipe(
            invalid_file, [], [], make_suggestions=False, search_github=False
        )
        self.assertIsNone(result)

    def test_locate_recipe_search_override_dirs(self):
        """Test locate_recipe searching in override directories."""
        import plistlib
        import tempfile

        recipe_dict = {
            "Description": "Test override",
            "Identifier": "com.example.test.override",
            "Input": {"NAME": "TestApp"},
            "ParentRecipe": "com.example.test",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            recipe_file = os.path.join(temp_dir, "TestApp.recipe")
            with open(recipe_file, "wb") as f:
                plistlib.dump(recipe_dict, f)

            result = autopkg.locate_recipe(
                "TestApp", [temp_dir], [], make_suggestions=False, search_github=False
            )
            self.assertEqual(result, recipe_file)

    def test_locate_recipe_search_recipe_dirs(self):
        """Test locate_recipe searching in recipe directories."""
        import plistlib
        import tempfile

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            recipe_file = os.path.join(temp_dir, "TestApp.recipe")
            with open(recipe_file, "wb") as f:
                plistlib.dump(recipe_dict, f)

            result = autopkg.locate_recipe(
                "TestApp", [], [temp_dir], make_suggestions=False, search_github=False
            )
            self.assertEqual(result, recipe_file)

    def test_locate_recipe_not_found(self):
        """Test locate_recipe when recipe is not found."""
        result = autopkg.locate_recipe(
            "NonExistentRecipe", [], [], make_suggestions=False, search_github=False
        )
        self.assertIsNone(result)

    def test_locate_recipe_subdirectory(self):
        """Test locate_recipe finding recipes in subdirectories."""
        import plistlib
        import tempfile

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            subdir = os.path.join(temp_dir, "subdir")
            os.makedirs(subdir)
            recipe_file = os.path.join(subdir, "TestApp.recipe")
            with open(recipe_file, "wb") as f:
                plistlib.dump(recipe_dict, f)

            result = autopkg.locate_recipe(
                "TestApp", [], [temp_dir], make_suggestions=False, search_github=False
            )
            self.assertEqual(result, recipe_file)

    # Tests for load_recipe function
    def test_load_recipe_simple_recipe(self):
        """Test load_recipe with a simple recipe file."""
        import plistlib
        import tempfile

        recipe_dict = {
            "Description": "Test recipe for loading",
            "Identifier": "com.example.test.load",
            "Input": {"NAME": "TestApp", "VERSION": "1.0"},
            "MinimumVersion": "2.0",
            "Process": [
                {"Processor": "URLDownloader"},
                {"Processor": "CodeSignatureVerifier"},
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            recipe_file = os.path.join(temp_dir, "TestApp.recipe")
            with open(recipe_file, "wb") as f:
                plistlib.dump(recipe_dict, f)

            result = autopkg.load_recipe(
                "TestApp", [], [temp_dir], make_suggestions=False, search_github=False
            )

            self.assertIsNotNone(result)
            self.assertEqual(result["Identifier"], "com.example.test.load")
            self.assertEqual(result["Description"], "Test recipe for loading")
            self.assertEqual(result["Input"]["NAME"], "TestApp")
            self.assertEqual(result["Input"]["VERSION"], "1.0")
            self.assertEqual(result["MinimumVersion"], "2.0")
            self.assertEqual(result["name"], "TestApp")
            self.assertEqual(result["RECIPE_PATH"], recipe_file)
            self.assertEqual(len(result["Process"]), 2)
            self.assertEqual(result["Process"][0]["Processor"], "URLDownloader")

    def test_load_recipe_with_parent_recipe(self):
        """Test load_recipe with an override that has a parent recipe."""
        import plistlib
        import tempfile

        # Create parent recipe
        parent_recipe_dict = {
            "Description": "Parent recipe",
            "Identifier": "com.example.parent",
            "Input": {"NAME": "ParentApp", "VERSION": "1.0"},
            "MinimumVersion": "1.0",
            "Process": [
                {"Processor": "URLDownloader"},
                {"Processor": "CodeSignatureVerifier"},
            ],
        }

        # Create child override
        child_recipe_dict = {
            "Description": "Child override",
            "Identifier": "com.example.child",
            "Input": {"NAME": "ChildApp", "VERSION": "2.0"},
            "MinimumVersion": "2.0",
            "ParentRecipe": "com.example.parent",
            "Process": [
                {"Processor": "MunkiImporter"},
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create parent recipe
            parent_file = os.path.join(temp_dir, "Parent.recipe")
            with open(parent_file, "wb") as f:
                plistlib.dump(parent_recipe_dict, f)

            # Create child override in same directory
            child_file = os.path.join(temp_dir, "Child.recipe")
            with open(child_file, "wb") as f:
                plistlib.dump(child_recipe_dict, f)

            result = autopkg.load_recipe(
                "Child", [], [temp_dir], make_suggestions=False, search_github=False
            )

            self.assertIsNotNone(result)
            self.assertEqual(result["Identifier"], "com.example.child")
            self.assertEqual(result["Description"], "Child override")
            # Child input should override parent input
            self.assertEqual(result["Input"]["NAME"], "ChildApp")
            self.assertEqual(result["Input"]["VERSION"], "2.0")
            # Should use higher MinimumVersion
            self.assertEqual(result["MinimumVersion"], "2.0")
            self.assertEqual(result["name"], "Child")
            self.assertEqual(result["RECIPE_PATH"], child_file)
            # Process should be parent + child
            self.assertEqual(len(result["Process"]), 3)
            self.assertEqual(result["Process"][0]["Processor"], "URLDownloader")
            self.assertEqual(result["Process"][1]["Processor"], "CodeSignatureVerifier")
            self.assertEqual(result["Process"][2]["Processor"], "MunkiImporter")
            # Should have parent recipes list
            self.assertIn("PARENT_RECIPES", result)
            self.assertEqual(result["PARENT_RECIPES"], [parent_file])

    def test_load_recipe_with_preprocessors(self):
        """Test load_recipe with preprocessors."""
        import plistlib
        import tempfile

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            recipe_file = os.path.join(temp_dir, "TestApp.recipe")
            with open(recipe_file, "wb") as f:
                plistlib.dump(recipe_dict, f)

            result = autopkg.load_recipe(
                "TestApp",
                [],
                [temp_dir],
                preprocessors=["Preprocessor1", "Preprocessor2"],
                make_suggestions=False,
                search_github=False,
            )

            self.assertIsNotNone(result)
            self.assertEqual(len(result["Process"]), 3)
            self.assertEqual(result["Process"][0]["Processor"], "Preprocessor1")
            self.assertEqual(result["Process"][1]["Processor"], "Preprocessor2")
            self.assertEqual(result["Process"][2]["Processor"], "URLDownloader")

    def test_load_recipe_with_postprocessors(self):
        """Test load_recipe with postprocessors."""
        import plistlib
        import tempfile

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            recipe_file = os.path.join(temp_dir, "TestApp.recipe")
            with open(recipe_file, "wb") as f:
                plistlib.dump(recipe_dict, f)

            result = autopkg.load_recipe(
                "TestApp",
                [],
                [temp_dir],
                postprocessors=["Postprocessor1", "Postprocessor2"],
                make_suggestions=False,
                search_github=False,
            )

            self.assertIsNotNone(result)
            self.assertEqual(len(result["Process"]), 3)
            self.assertEqual(result["Process"][0]["Processor"], "URLDownloader")
            self.assertEqual(result["Process"][1]["Processor"], "Postprocessor1")
            self.assertEqual(result["Process"][2]["Processor"], "Postprocessor2")

    def test_load_recipe_with_pre_and_postprocessors(self):
        """Test load_recipe with both preprocessors and postprocessors."""
        import plistlib
        import tempfile

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "Input": {"NAME": "TestApp"},
            "Process": [
                {"Processor": "URLDownloader"},
                {"Processor": "CodeSignatureVerifier"},
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            recipe_file = os.path.join(temp_dir, "TestApp.recipe")
            with open(recipe_file, "wb") as f:
                plistlib.dump(recipe_dict, f)

            result = autopkg.load_recipe(
                "TestApp",
                [],
                [temp_dir],
                preprocessors=["Preprocessor1"],
                postprocessors=["Postprocessor1"],
                make_suggestions=False,
                search_github=False,
            )

            self.assertIsNotNone(result)
            self.assertEqual(len(result["Process"]), 4)
            self.assertEqual(result["Process"][0]["Processor"], "Preprocessor1")
            self.assertEqual(result["Process"][1]["Processor"], "URLDownloader")
            self.assertEqual(result["Process"][2]["Processor"], "CodeSignatureVerifier")
            self.assertEqual(result["Process"][3]["Processor"], "Postprocessor1")

    def test_load_recipe_not_found(self):
        """Test load_recipe when recipe is not found."""
        result = autopkg.load_recipe(
            "NonExistentRecipe", [], [], make_suggestions=False, search_github=False
        )
        self.assertIsNone(result)

    def test_load_recipe_none_dirs(self):
        """Test load_recipe with None directories."""
        import plistlib
        import tempfile

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".recipe", delete=False
        ) as f:
            plistlib.dump(recipe_dict, f)
            temp_file = f.name

        try:
            result = autopkg.load_recipe(
                temp_file, None, None, make_suggestions=False, search_github=False
            )
            self.assertIsNotNone(result)
            self.assertEqual(result["Identifier"], "com.example.test")
        finally:
            os.unlink(temp_file)

    def test_load_recipe_override_with_trust_info(self):
        """Test load_recipe with an override containing trust info."""
        import plistlib
        import tempfile

        # Create parent recipe
        parent_recipe_dict = {
            "Description": "Parent recipe",
            "Identifier": "com.example.parent",
            "Input": {"NAME": "ParentApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        # Create override with trust info
        override_dict = {
            "Description": "Override with trust",
            "Identifier": "com.example.override",
            "Input": {"NAME": "OverrideApp"},
            "ParentRecipe": "com.example.parent",
            "ParentRecipeTrustInfo": {
                "non_core_processors": {},
                "parent_recipes": {
                    "com.example.parent": {
                        "path": "~/recipes/Parent.recipe",
                        "sha256_hash": "abc123",
                    }
                },
            },
            "Process": [],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create parent recipe
            parent_file = os.path.join(temp_dir, "Parent.recipe")
            with open(parent_file, "wb") as f:
                plistlib.dump(parent_recipe_dict, f)

            # Create override directory
            override_dir = os.path.join(temp_dir, "overrides")
            os.makedirs(override_dir)
            override_file = os.path.join(override_dir, "Override.recipe")
            with open(override_file, "wb") as f:
                plistlib.dump(override_dict, f)

            result = autopkg.load_recipe(
                "Override",
                [override_dir],
                [temp_dir],
                make_suggestions=False,
                search_github=False,
            )

            self.assertIsNotNone(result)
            self.assertEqual(result["Identifier"], "com.example.override")
            # Trust info should be preserved
            self.assertIn("ParentRecipeTrustInfo", result)
            self.assertEqual(result["ParentRecipe"], "com.example.parent")

    def test_load_recipe_minimum_version_comparison(self):
        """Test load_recipe MinimumVersion handling with parent and child."""
        import plistlib
        import tempfile

        # Create parent recipe with lower MinimumVersion
        parent_recipe_dict = {
            "Description": "Parent recipe",
            "Identifier": "com.example.parent",
            "Input": {"NAME": "ParentApp"},
            "MinimumVersion": "1.0",
            "Process": [{"Processor": "URLDownloader"}],
        }

        # Create child with higher MinimumVersion
        child_recipe_dict = {
            "Description": "Child override",
            "Identifier": "com.example.child",
            "Input": {"NAME": "ChildApp"},
            "MinimumVersion": "2.5",
            "ParentRecipe": "com.example.parent",
            "Process": [],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create parent recipe
            parent_file = os.path.join(temp_dir, "Parent.recipe")
            with open(parent_file, "wb") as f:
                plistlib.dump(parent_recipe_dict, f)

            # Create child override
            child_file = os.path.join(temp_dir, "Child.recipe")
            with open(child_file, "wb") as f:
                plistlib.dump(child_recipe_dict, f)

            result = autopkg.load_recipe(
                "Child", [], [temp_dir], make_suggestions=False, search_github=False
            )

            self.assertIsNotNone(result)
            # Should use higher MinimumVersion from child
            self.assertEqual(result["MinimumVersion"], "2.5")

    def test_load_recipe_missing_minimum_version(self):
        """Test load_recipe when MinimumVersion is missing from recipes."""
        import plistlib
        import tempfile

        # Create parent recipe without MinimumVersion
        parent_recipe_dict = {
            "Description": "Parent recipe",
            "Identifier": "com.example.parent",
            "Input": {"NAME": "ParentApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        # Create child without MinimumVersion
        child_recipe_dict = {
            "Description": "Child override",
            "Identifier": "com.example.child",
            "Input": {"NAME": "ChildApp"},
            "ParentRecipe": "com.example.parent",
            "Process": [],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create parent recipe
            parent_file = os.path.join(temp_dir, "Parent.recipe")
            with open(parent_file, "wb") as f:
                plistlib.dump(parent_recipe_dict, f)

            # Create child override
            child_file = os.path.join(temp_dir, "Child.recipe")
            with open(child_file, "wb") as f:
                plistlib.dump(child_recipe_dict, f)

            result = autopkg.load_recipe(
                "Child", [], [temp_dir], make_suggestions=False, search_github=False
            )

            self.assertIsNotNone(result)
            # Should default to "0" when missing
            self.assertEqual(result["MinimumVersion"], "0")

    @patch("sys.argv", ["autopkg", "audit", "test.recipe"])
    def test_audit_basic_recipe_no_issues(self):
        """Test audit command with a basic recipe that has no issues."""
        mock_recipe = {
            "RECIPE_PATH": "/path/to/test.recipe",
            "Process": [
                {"Processor": "URLDownloader"},
                {"Processor": "CodeSignatureVerifier"},
            ],
            "Input": {"test_key": "test_value"},
        }

        with patch.object(
            autopkg, "gen_common_parser"
        ) as mock_parser_gen, patch.object(
            autopkg, "add_search_and_override_dir_options"
        ), patch.object(
            autopkg, "common_parse"
        ) as mock_parse, patch.object(
            autopkg, "get_override_dirs"
        ) as mock_get_override_dirs, patch.object(
            autopkg, "get_search_dirs"
        ) as mock_get_search_dirs, patch.object(
            autopkg, "load_recipe"
        ) as mock_load_recipe, patch.object(
            autopkg, "find_http_urls_in_recipe"
        ) as mock_find_urls, patch.object(
            autopkg, "core_processor_names"
        ) as mock_core_processors, patch.object(
            autopkg, "log"
        ) as mock_log:

            mock_parser = Mock()
            mock_parser.add_option = Mock()
            mock_parser_gen.return_value = mock_parser
            mock_options = Mock()
            mock_options.recipe_list = None
            mock_options.plist = False
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_parse.return_value = (mock_options, ["test.recipe"])
            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]
            mock_load_recipe.return_value = mock_recipe
            mock_find_urls.return_value = {}  # No HTTP URLs
            mock_core_processors.return_value = [
                "URLDownloader",
                "CodeSignatureVerifier",
            ]

            result = autopkg.audit(["autopkg", "audit", "test.recipe"])

            # Should complete without error
            self.assertIsNone(result)
            mock_log.assert_called_with("test.recipe: no audit flags triggered.")

    @patch("sys.argv", ["autopkg", "audit", "test.recipe"])
    def test_audit_missing_code_signature_verifier(self):
        """Test audit command flagging missing CodeSignatureVerifier."""
        mock_recipe = {
            "RECIPE_PATH": "/path/to/test.recipe",
            "Process": [
                {"Processor": "URLDownloader"}  # Missing CodeSignatureVerifier
            ],
            "Input": {},
        }

        with patch.object(
            autopkg, "gen_common_parser"
        ) as mock_parser_gen, patch.object(
            autopkg, "add_search_and_override_dir_options"
        ), patch.object(
            autopkg, "common_parse"
        ) as mock_parse, patch.object(
            autopkg, "get_override_dirs"
        ) as mock_get_override_dirs, patch.object(
            autopkg, "get_search_dirs"
        ) as mock_get_search_dirs, patch.object(
            autopkg, "load_recipe"
        ) as mock_load_recipe, patch.object(
            autopkg, "find_http_urls_in_recipe"
        ) as mock_find_urls, patch.object(
            autopkg, "core_processor_names"
        ) as mock_core_processors, patch.object(
            autopkg, "log"
        ) as mock_log:

            mock_parser = Mock()
            mock_parser.add_option = Mock()
            mock_parser_gen.return_value = mock_parser
            mock_options = Mock()
            mock_options.recipe_list = None
            mock_options.plist = False
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_parse.return_value = (mock_options, ["test.recipe"])
            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]
            mock_load_recipe.return_value = mock_recipe
            mock_find_urls.return_value = {}
            mock_core_processors.return_value = [
                "URLDownloader",
                "CodeSignatureVerifier",
            ]

            result = autopkg.audit(["autopkg", "audit", "test.recipe"])

            self.assertIsNone(result)
            # Should log the missing CodeSignatureVerifier warning
            mock_log.assert_any_call("    Missing CodeSignatureVerifier")

    @patch("sys.argv", ["autopkg", "audit", "test.recipe"])
    def test_audit_http_urls_found(self):
        """Test audit command flagging HTTP URLs in recipe."""
        mock_recipe = {
            "RECIPE_PATH": "/path/to/test.recipe",
            "Process": [{"Processor": "URLDownloader"}],
            "Input": {"url": "http://insecure.example.com/file.dmg"},
        }

        with patch.object(
            autopkg, "gen_common_parser"
        ) as mock_parser_gen, patch.object(
            autopkg, "add_search_and_override_dir_options"
        ), patch.object(
            autopkg, "common_parse"
        ) as mock_parse, patch.object(
            autopkg, "get_override_dirs"
        ) as mock_get_override_dirs, patch.object(
            autopkg, "get_search_dirs"
        ) as mock_get_search_dirs, patch.object(
            autopkg, "load_recipe"
        ) as mock_load_recipe, patch.object(
            autopkg, "find_http_urls_in_recipe"
        ) as mock_find_urls, patch.object(
            autopkg, "core_processor_names"
        ) as mock_core_processors, patch.object(
            autopkg, "printplist"
        ) as mock_printplist, patch.object(
            autopkg, "log"
        ) as mock_log:

            mock_parser = Mock()
            mock_parser.add_option = Mock()
            mock_parser_gen.return_value = mock_parser
            mock_options = Mock()
            mock_options.recipe_list = None
            mock_options.plist = False
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_parse.return_value = (mock_options, ["test.recipe"])
            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]
            mock_load_recipe.return_value = mock_recipe
            mock_find_urls.return_value = {
                "Input": {"url": "http://insecure.example.com/file.dmg"}
            }
            mock_core_processors.return_value = ["URLDownloader"]

            result = autopkg.audit(["autopkg", "audit", "test.recipe"])

            self.assertIsNone(result)
            mock_log.assert_any_call(
                "    The following http URLs were found in the recipe:"
            )
            mock_printplist.assert_called_once()

    @patch("sys.argv", ["autopkg", "audit", "test.recipe"])
    def test_audit_non_core_processors(self):
        """Test audit command flagging non-core processors."""
        mock_recipe = {
            "RECIPE_PATH": "/path/to/test.recipe",
            "Process": [
                {"Processor": "URLDownloader"},
                {"Processor": "CustomProcessor"},  # Non-core processor
            ],
            "Input": {},
        }

        with patch.object(
            autopkg, "gen_common_parser"
        ) as mock_parser_gen, patch.object(
            autopkg, "add_search_and_override_dir_options"
        ), patch.object(
            autopkg, "common_parse"
        ) as mock_parse, patch.object(
            autopkg, "get_override_dirs"
        ) as mock_get_override_dirs, patch.object(
            autopkg, "get_search_dirs"
        ) as mock_get_search_dirs, patch.object(
            autopkg, "load_recipe"
        ) as mock_load_recipe, patch.object(
            autopkg, "find_http_urls_in_recipe"
        ) as mock_find_urls, patch.object(
            autopkg, "core_processor_names"
        ) as mock_core_processors, patch.object(
            autopkg, "log"
        ) as mock_log:

            mock_parser = Mock()
            mock_parser.add_option = Mock()
            mock_parser_gen.return_value = mock_parser
            mock_options = Mock()
            mock_options.recipe_list = None
            mock_options.plist = False
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_parse.return_value = (mock_options, ["test.recipe"])
            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]
            mock_load_recipe.return_value = mock_recipe
            mock_find_urls.return_value = {}
            mock_core_processors.return_value = [
                "URLDownloader"
            ]  # CustomProcessor not in core

            result = autopkg.audit(["autopkg", "audit", "test.recipe"])

            self.assertIsNone(result)
            mock_log.assert_any_call(
                "    The following processors are non-core and can execute "
                "arbitrary code, performing any action."
            )
            mock_log.assert_any_call("        CustomProcessor")

    @patch("sys.argv", ["autopkg", "audit", "test.recipe"])
    def test_audit_modification_processors(self):
        """Test audit command flagging modification processors before creator processors."""
        mock_recipe = {
            "RECIPE_PATH": "/path/to/test.recipe",
            "Process": [
                {"Processor": "URLDownloader"},
                {"Processor": "Copier"},  # Modification processor
                {"Processor": "PkgCreator"},  # Creator processor
            ],
            "Input": {},
        }

        with patch.object(
            autopkg, "gen_common_parser"
        ) as mock_parser_gen, patch.object(
            autopkg, "add_search_and_override_dir_options"
        ), patch.object(
            autopkg, "common_parse"
        ) as mock_parse, patch.object(
            autopkg, "get_override_dirs"
        ) as mock_get_override_dirs, patch.object(
            autopkg, "get_search_dirs"
        ) as mock_get_search_dirs, patch.object(
            autopkg, "load_recipe"
        ) as mock_load_recipe, patch.object(
            autopkg, "find_http_urls_in_recipe"
        ) as mock_find_urls, patch.object(
            autopkg, "core_processor_names"
        ) as mock_core_processors, patch.object(
            autopkg, "log"
        ) as mock_log:

            mock_parser = Mock()
            mock_parser.add_option = Mock()
            mock_parser_gen.return_value = mock_parser
            mock_options = Mock()
            mock_options.recipe_list = None
            mock_options.plist = False
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_parse.return_value = (mock_options, ["test.recipe"])
            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]
            mock_load_recipe.return_value = mock_recipe
            mock_find_urls.return_value = {}
            mock_core_processors.return_value = [
                "URLDownloader",
                "Copier",
                "PkgCreator",
            ]

            result = autopkg.audit(["autopkg", "audit", "test.recipe"])

            self.assertIsNone(result)
            mock_log.assert_any_call(
                "    The following processors make modifications and their "
                "use in this recipe should be more closely inspected:"
            )
            mock_log.assert_any_call("        Copier")

    @patch("sys.argv", ["autopkg", "audit", "--plist", "test.recipe"])
    def test_audit_plist_output(self):
        """Test audit command with plist output format."""
        mock_recipe = {
            "RECIPE_PATH": "/path/to/test.recipe",
            "Process": [{"Processor": "URLDownloader"}],
            "Input": {"url": "http://insecure.example.com/file.dmg"},
        }

        with patch.object(
            autopkg, "gen_common_parser"
        ) as mock_parser_gen, patch.object(
            autopkg, "add_search_and_override_dir_options"
        ), patch.object(
            autopkg, "common_parse"
        ) as mock_parse, patch.object(
            autopkg, "get_override_dirs"
        ) as mock_get_override_dirs, patch.object(
            autopkg, "get_search_dirs"
        ) as mock_get_search_dirs, patch.object(
            autopkg, "load_recipe"
        ) as mock_load_recipe, patch.object(
            autopkg, "find_http_urls_in_recipe"
        ) as mock_find_urls, patch.object(
            autopkg, "core_processor_names"
        ) as mock_core_processors, patch(
            "builtins.print"
        ) as mock_print:

            mock_parser = Mock()
            mock_parser.add_option = Mock()
            mock_parser_gen.return_value = mock_parser
            mock_options = Mock()
            mock_options.recipe_list = None
            mock_options.plist = True  # Plist output format
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_parse.return_value = (mock_options, ["test.recipe"])
            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]
            mock_load_recipe.return_value = mock_recipe
            mock_find_urls.return_value = {
                "Input": {"url": "http://insecure.example.com/file.dmg"}
            }
            mock_core_processors.return_value = ["URLDownloader"]

            result = autopkg.audit(["autopkg", "audit", "--plist", "test.recipe"])

            self.assertIsNone(result)
            # Should print plist format output
            mock_print.assert_called_once()
            args = mock_print.call_args[0]
            self.assertTrue(args[0].startswith(b"<?xml"))  # Plist format

    @patch("sys.argv", ["autopkg", "audit", "--recipe-list", "/path/to/recipes.txt"])
    def test_audit_recipe_list_file(self):
        """Test audit command with recipe list from file."""
        mock_recipe = {
            "RECIPE_PATH": "/path/to/test.recipe",
            "Process": [{"Processor": "URLDownloader"}],
            "Input": {},
        }

        with patch.object(
            autopkg, "gen_common_parser"
        ) as mock_parser_gen, patch.object(
            autopkg, "add_search_and_override_dir_options"
        ), patch.object(
            autopkg, "common_parse"
        ) as mock_parse, patch.object(
            autopkg, "get_override_dirs"
        ) as mock_get_override_dirs, patch.object(
            autopkg, "get_search_dirs"
        ) as mock_get_search_dirs, patch.object(
            autopkg, "parse_recipe_list"
        ) as mock_parse_recipe_list, patch.object(
            autopkg, "load_recipe"
        ) as mock_load_recipe, patch.object(
            autopkg, "find_http_urls_in_recipe"
        ) as mock_find_urls, patch.object(
            autopkg, "core_processor_names"
        ) as mock_core_processors:

            mock_parser = Mock()
            mock_parser.add_option = Mock()
            mock_parser_gen.return_value = mock_parser
            mock_options = Mock()
            mock_options.recipe_list = "/path/to/recipes.txt"
            mock_options.plist = False
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_parse.return_value = (mock_options, [])  # No command line recipes
            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]
            mock_parse_recipe_list.return_value = {
                "recipes": ["test.recipe", "other.recipe"]
            }
            mock_load_recipe.return_value = mock_recipe
            mock_find_urls.return_value = {}
            mock_core_processors.return_value = ["URLDownloader"]

            result = autopkg.audit(
                ["autopkg", "audit", "--recipe-list", "/path/to/recipes.txt"]
            )

            self.assertIsNone(result)
            # Should load recipes from the file
            mock_parse_recipe_list.assert_called_once_with("/path/to/recipes.txt")
            # Should process both recipes
            self.assertEqual(mock_load_recipe.call_count, 2)

    @patch("sys.argv", ["autopkg", "audit"])
    def test_audit_no_recipes_provided(self):
        """Test audit command with no recipes provided."""
        with patch.object(
            autopkg, "gen_common_parser"
        ) as mock_parser_gen, patch.object(
            autopkg, "add_search_and_override_dir_options"
        ), patch.object(
            autopkg, "common_parse"
        ) as mock_parse, patch.object(
            autopkg, "get_override_dirs"
        ) as mock_get_override_dirs, patch.object(
            autopkg, "get_search_dirs"
        ) as mock_get_search_dirs, patch.object(
            autopkg, "log_err"
        ) as mock_log_err:

            mock_parser = Mock()
            mock_parser.add_option = Mock()
            mock_parser.get_usage = Mock(return_value="Usage info")
            mock_parser_gen.return_value = mock_parser
            mock_options = Mock()
            mock_options.recipe_list = None
            mock_options.plist = False
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_parse.return_value = (mock_options, [])  # No recipes
            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]

            result = autopkg.audit(["autopkg", "audit"])

            self.assertEqual(result, -1)
            mock_log_err.assert_called_with("Usage info")

    @patch("sys.argv", ["autopkg", "audit", "nonexistent.recipe"])
    def test_audit_recipe_not_found(self):
        """Test audit command with a recipe that cannot be found."""
        with patch.object(
            autopkg, "gen_common_parser"
        ) as mock_parser_gen, patch.object(
            autopkg, "add_search_and_override_dir_options"
        ), patch.object(
            autopkg, "common_parse"
        ) as mock_parse, patch.object(
            autopkg, "get_override_dirs"
        ) as mock_get_override_dirs, patch.object(
            autopkg, "get_search_dirs"
        ) as mock_get_search_dirs, patch.object(
            autopkg, "load_recipe"
        ) as mock_load_recipe, patch.object(
            autopkg, "log_err"
        ) as mock_log_err:

            mock_parser = Mock()
            mock_parser.add_option = Mock()
            mock_parser_gen.return_value = mock_parser
            mock_options = Mock()
            mock_options.recipe_list = None
            mock_options.plist = False
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_parse.return_value = (mock_options, ["nonexistent.recipe"])
            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]
            mock_load_recipe.return_value = None  # Recipe not found

            result = autopkg.audit(["autopkg", "audit", "nonexistent.recipe"])

            self.assertIsNone(result)
            mock_log_err.assert_called_with(
                "No valid recipe found for nonexistent.recipe"
            )

    def test_list_recipes_basic_output(self):
        """Test list_recipes command with basic output format."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.get_recipe_list"
        ) as mock_get_recipe_list, patch(
            "builtins.print"
        ) as mock_print:

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_options.with_identifiers = False
            mock_options.with_paths = False
            mock_options.plist = False
            mock_options.show_all = False
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, [])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]

            mock_recipes = [
                {"Name": "TestApp.download"},
                {"Name": "AnotherApp.munki"},
                {"Name": "Firefox.download"},
            ]
            mock_get_recipe_list.return_value = mock_recipes

            result = autopkg.list_recipes(["autopkg", "list-recipes"])

            self.assertIsNone(result)
            mock_print.assert_called_once()
            # Check that recipes are sorted alphabetically (case-insensitive)
            printed_output = mock_print.call_args[0][0]
            lines = printed_output.split("\n")
            self.assertIn("AnotherApp.munki", lines[0])
            self.assertIn("Firefox.download", lines[1])
            self.assertIn("TestApp.download", lines[2])

    def test_list_recipes_with_identifiers(self):
        """Test list_recipes command with identifiers included."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.get_recipe_list"
        ) as mock_get_recipe_list, patch(
            "builtins.print"
        ) as mock_print:

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_options.with_identifiers = True
            mock_options.with_paths = False
            mock_options.plist = False
            mock_options.show_all = False
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, [])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]

            mock_recipes = [
                {
                    "Name": "TestApp.download",
                    "Identifier": "com.github.autopkg.download.testapp",
                },
                {
                    "Name": "Firefox.download",
                    "Identifier": "com.github.autopkg.download.firefox",
                },
            ]
            mock_get_recipe_list.return_value = mock_recipes

            result = autopkg.list_recipes(
                ["autopkg", "list-recipes", "--with-identifiers"]
            )

            self.assertIsNone(result)
            mock_print.assert_called_once()
            printed_output = mock_print.call_args[0][0]
            # Should include identifiers in output
            self.assertIn("com.github.autopkg.download.firefox", printed_output)
            self.assertIn("com.github.autopkg.download.testapp", printed_output)

    def test_list_recipes_with_paths(self):
        """Test list_recipes command with paths included."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.get_recipe_list"
        ) as mock_get_recipe_list, patch(
            "builtins.print"
        ) as mock_print, patch.dict(
            "os.environ", {"HOME": "/Users/testuser"}
        ):

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_options.with_identifiers = False
            mock_options.with_paths = True
            mock_options.plist = False
            mock_options.show_all = False
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, [])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]

            mock_recipes = [
                {
                    "Name": "TestApp.download",
                    "Path": "/Users/testuser/Library/AutoPkg/RecipeRepos/recipes/TestApp.download.recipe",
                },
                {
                    "Name": "Firefox.download",
                    "Path": "/recipes/Firefox.download.recipe",
                },
            ]
            mock_get_recipe_list.return_value = mock_recipes

            result = autopkg.list_recipes(["autopkg", "list-recipes", "--with-paths"])

            self.assertIsNone(result)
            mock_print.assert_called_once()
            printed_output = mock_print.call_args[0][0]
            # Should replace home directory with ~
            self.assertIn(
                "~/Library/AutoPkg/RecipeRepos/recipes/TestApp.download.recipe",
                printed_output,
            )
            self.assertIn("/recipes/Firefox.download.recipe", printed_output)

    def test_list_recipes_plist_format(self):
        """Test list_recipes command with plist output format."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.get_recipe_list"
        ) as mock_get_recipe_list, patch(
            "builtins.print"
        ) as mock_print, patch(
            "plistlib.dumps"
        ) as mock_dumps:

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_options.with_identifiers = False
            mock_options.with_paths = False
            mock_options.plist = True
            mock_options.show_all = False
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, [])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]

            mock_recipes = [
                {
                    "Name": "TestApp.download",
                    "Identifier": "com.github.autopkg.download.testapp",
                    "Path": "/recipes/TestApp.download.recipe",
                },
            ]
            mock_get_recipe_list.return_value = mock_recipes
            mock_dumps.return_value = b'<plist version="1.0">...</plist>'

            result = autopkg.list_recipes(["autopkg", "list-recipes", "--plist"])

            self.assertIsNone(result)
            mock_dumps.assert_called_once_with(mock_recipes)
            mock_print.assert_called_once_with('<plist version="1.0">...</plist>')

    def test_list_recipes_show_all_with_augmented_list(self):
        """Test list_recipes command with show-all option and augmented list."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.get_recipe_list"
        ) as mock_get_recipe_list, patch(
            "builtins.print"
        ):

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_options.with_identifiers = True
            mock_options.with_paths = False
            mock_options.plist = False
            mock_options.show_all = True
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, [])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]

            mock_recipes = [
                {
                    "Name": "TestApp.download",
                    "Identifier": "com.github.autopkg.download.testapp",
                },
                {
                    "Name": "TestApp.download",  # Duplicate name (override)
                    "Identifier": "local.testapp.override",
                },
            ]
            mock_get_recipe_list.return_value = mock_recipes

            result = autopkg.list_recipes(
                ["autopkg", "list-recipes", "--show-all", "--with-identifiers"]
            )

            self.assertIsNone(result)
            mock_get_recipe_list.assert_called_once_with(
                override_dirs=["/overrides"],
                search_dirs=["/recipes"],
                augmented_list=True,
                show_all=True,
            )

    def test_list_recipes_show_all_without_augmented_list_error(self):
        """Test list_recipes command with show-all option but no augmented list flags."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse, patch("autopkg.log_err") as mock_log_err:

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_options.with_identifiers = False
            mock_options.with_paths = False
            mock_options.plist = False
            mock_options.show_all = True
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, [])

            result = autopkg.list_recipes(["autopkg", "list-recipes", "--show-all"])

            self.assertEqual(result, -1)
            mock_log_err.assert_called_with(
                "The '--show-all' option is only valid when used with "
                "'--with-paths', '--with-identifiers', or '--plist' options."
            )

    def test_list_recipes_plist_with_identifiers_error(self):
        """Test list_recipes command with plist and identifiers options (invalid combination)."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse, patch("autopkg.log_err") as mock_log_err:

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_options.with_identifiers = True
            mock_options.with_paths = False
            mock_options.plist = True
            mock_options.show_all = False
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, [])

            result = autopkg.list_recipes(
                ["autopkg", "list-recipes", "--plist", "--with-identifiers"]
            )

            self.assertEqual(result, -1)
            mock_log_err.assert_called_with(
                "It is invalid to specify '--with-identifiers' or "
                "'--with-paths' with '--plist'."
            )

    def test_list_recipes_plist_with_paths_error(self):
        """Test list_recipes command with plist and paths options (invalid combination)."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse, patch("autopkg.log_err") as mock_log_err:

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_options.with_identifiers = False
            mock_options.with_paths = True
            mock_options.plist = True
            mock_options.show_all = False
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, [])

            result = autopkg.list_recipes(
                ["autopkg", "list-recipes", "--plist", "--with-paths"]
            )

            self.assertEqual(result, -1)
            mock_log_err.assert_called_with(
                "It is invalid to specify '--with-identifiers' or "
                "'--with-paths' with '--plist'."
            )

    def test_list_recipes_with_identifiers_and_paths(self):
        """Test list_recipes command with both identifiers and paths."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.get_recipe_list"
        ) as mock_get_recipe_list, patch(
            "builtins.print"
        ) as mock_print, patch.dict(
            "os.environ", {"HOME": "/Users/testuser"}
        ):

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_options.with_identifiers = True
            mock_options.with_paths = True
            mock_options.plist = False
            mock_options.show_all = False
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, [])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]

            mock_recipes = [
                {
                    "Name": "TestApp.download",
                    "Identifier": "com.github.autopkg.download.testapp",
                    "Path": "/Users/testuser/recipes/TestApp.download.recipe",
                },
            ]
            mock_get_recipe_list.return_value = mock_recipes

            result = autopkg.list_recipes(
                ["autopkg", "list-recipes", "--with-identifiers", "--with-paths"]
            )

            self.assertIsNone(result)
            mock_print.assert_called_once()
            printed_output = mock_print.call_args[0][0]
            # Should include both identifier and path
            self.assertIn("com.github.autopkg.download.testapp", printed_output)
            self.assertIn("~/recipes/TestApp.download.recipe", printed_output)

    def test_list_recipes_empty_recipe_list(self):
        """Test list_recipes command with empty recipe list."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.get_recipe_list"
        ) as mock_get_recipe_list, patch(
            "builtins.print"
        ) as mock_print:

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_options.with_identifiers = False
            mock_options.with_paths = False
            mock_options.plist = False
            mock_options.show_all = False
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, [])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]

            mock_get_recipe_list.return_value = []

            result = autopkg.list_recipes(["autopkg", "list-recipes"])

            self.assertIsNone(result)
            mock_print.assert_called_once_with("")

    def test_list_recipes_custom_directories(self):
        """Test list_recipes command with custom override and search directories."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse, patch(
            "autopkg.get_recipe_list"
        ) as mock_get_recipe_list, patch(
            "builtins.print"
        ):

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_options.with_identifiers = False
            mock_options.with_paths = False
            mock_options.plist = False
            mock_options.show_all = False
            mock_options.override_dirs = ["/custom/overrides"]
            mock_options.search_dirs = ["/custom/recipes"]
            mock_common_parse.return_value = (mock_options, [])

            mock_recipes = [{"Name": "CustomApp.download"}]
            mock_get_recipe_list.return_value = mock_recipes

            result = autopkg.list_recipes(
                [
                    "autopkg",
                    "list-recipes",
                    "--override-dir",
                    "/custom/overrides",
                    "--search-dir",
                    "/custom/recipes",
                ]
            )

            self.assertIsNone(result)
            mock_get_recipe_list.assert_called_once_with(
                override_dirs=["/custom/overrides"],
                search_dirs=["/custom/recipes"],
                augmented_list=False,
                show_all=False,
            )

    def test_list_recipes_missing_identifier_in_recipe(self):
        """Test list_recipes command when recipe is missing Identifier."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.get_recipe_list"
        ) as mock_get_recipe_list, patch(
            "builtins.print"
        ) as mock_print:

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_options.with_identifiers = True
            mock_options.with_paths = False
            mock_options.plist = False
            mock_options.show_all = False
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, [])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]

            mock_recipes = [
                {
                    "Name": "TestApp.download",
                    # Missing Identifier key
                },
            ]
            mock_get_recipe_list.return_value = mock_recipes

            result = autopkg.list_recipes(
                ["autopkg", "list-recipes", "--with-identifiers"]
            )

            self.assertIsNone(result)
            mock_print.assert_called_once()
            printed_output = mock_print.call_args[0][0]
            # Should include recipe name even without identifier
            self.assertIn("TestApp.download", printed_output)

    def test_list_recipes_missing_path_in_recipe(self):
        """Test list_recipes command when recipe is missing Path."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.get_recipe_list"
        ) as mock_get_recipe_list, patch(
            "builtins.print"
        ) as mock_print:

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_options.with_identifiers = False
            mock_options.with_paths = True
            mock_options.plist = False
            mock_options.show_all = False
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, [])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]

            mock_recipes = [
                {
                    "Name": "TestApp.download",
                    # Missing Path key
                },
            ]
            mock_get_recipe_list.return_value = mock_recipes

            result = autopkg.list_recipes(["autopkg", "list-recipes", "--with-paths"])

            self.assertIsNone(result)
            mock_print.assert_called_once()
            printed_output = mock_print.call_args[0][0]
            # Should include recipe name even without path
            self.assertIn("TestApp.download", printed_output)

    def test_list_recipes_case_insensitive_sorting(self):
        """Test list_recipes command sorts recipes case-insensitively."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.get_recipe_list"
        ) as mock_get_recipe_list, patch(
            "builtins.print"
        ) as mock_print:

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_options.with_identifiers = False
            mock_options.with_paths = False
            mock_options.plist = False
            mock_options.show_all = False
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, [])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]

            # Mix of upper and lower case
            mock_recipes = [
                {"Name": "zApp.download"},
                {"Name": "AnotherApp.munki"},
                {"Name": "bApp.pkg"},
                {"Name": "Apple.download"},
            ]
            mock_get_recipe_list.return_value = mock_recipes

            result = autopkg.list_recipes(["autopkg", "list-recipes"])

            self.assertIsNone(result)
            mock_print.assert_called_once()
            printed_output = mock_print.call_args[0][0]
            lines = printed_output.split("\n")
            # Should be sorted case-insensitively: AnotherApp, Apple, bApp, zApp
            self.assertIn("AnotherApp.munki", lines[0])
            self.assertIn("Apple.download", lines[1])
            self.assertIn("bApp.pkg", lines[2])
            self.assertIn("zApp.download", lines[3])

    def test_list_recipes_deduplication(self):
        """Test list_recipes command removes duplicate output strings."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.get_recipe_list"
        ) as mock_get_recipe_list, patch(
            "builtins.print"
        ) as mock_print:

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_options.with_identifiers = False
            mock_options.with_paths = False
            mock_options.plist = False
            mock_options.show_all = False
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, [])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]

            # Identical recipes that would produce duplicate output
            mock_recipes = [
                {"Name": "TestApp.download"},
                {"Name": "TestApp.download"},  # Duplicate
                {"Name": "AnotherApp.munki"},
            ]
            mock_get_recipe_list.return_value = mock_recipes

            result = autopkg.list_recipes(["autopkg", "list-recipes"])

            self.assertIsNone(result)
            mock_print.assert_called_once()
            printed_output = mock_print.call_args[0][0]
            lines = printed_output.split("\n")
            # Should only have 2 lines (duplicates removed)
            self.assertEqual(len(lines), 2)
            self.assertIn("AnotherApp.munki", lines[0])
            self.assertIn("TestApp.download", lines[1])


if __name__ == "__main__":
    unittest.main()
