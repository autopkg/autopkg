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
import plistlib
import sys
import unittest
import unittest.mock
from io import StringIO
from tempfile import NamedTemporaryFile, TemporaryDirectory
from unittest.mock import Mock, patch

# Add the Code directory to the Python path to resolve autopkg dependencies
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

autopkg = imp.load_source(
    "autopkg", os.path.join(os.path.dirname(__file__), "..", "autopkg")
)


class TestAutoPkgRecipes(unittest.TestCase):
    """Test cases for recipe-related functions of AutoPkg."""

    def setUp(self):
        """Set up test fixtures with a temporary directory."""
        self.tmp_dir = TemporaryDirectory()

    def tearDown(self):
        """Clean up test fixtures."""
        self.tmp_dir.cleanup()

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

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        with NamedTemporaryFile(mode="wb", suffix=".recipe", delete=False) as f:
            plistlib.dump(recipe_dict, f)
            temp_file = f.name

        try:
            result = autopkg.valid_recipe_file(temp_file)
            self.assertTrue(result)
        finally:
            os.unlink(temp_file)

    def test_valid_recipe_file_invalid_file(self):
        """Test valid_recipe_file with an invalid recipe file."""

        # Create a recipe without required keys (missing Identifier and Input)
        recipe_dict = {
            "Description": "Invalid recipe",
            "Process": [{"Processor": "URLDownloader"}],
        }

        with NamedTemporaryFile(mode="wb", suffix=".recipe", delete=False) as f:
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

        # Create a malformed plist file
        with NamedTemporaryFile(mode="w", suffix=".recipe", delete=False) as f:
            f.write("This is not a valid plist file")
            temp_file = f.name

        try:
            result = autopkg.valid_recipe_file(temp_file)
            self.assertFalse(result)
        finally:
            os.unlink(temp_file)

    def test_valid_override_file_valid_file(self):
        """Test valid_override_file with a valid override file."""

        override_dict = {
            "Description": "Test override",
            "Identifier": "com.example.test.override",
            "Input": {"NAME": "TestApp"},
            "ParentRecipe": "com.example.test.download",
        }

        with NamedTemporaryFile(mode="wb", suffix=".recipe", delete=False) as f:
            plistlib.dump(override_dict, f)
            temp_file = f.name

        try:
            result = autopkg.valid_override_file(temp_file)
            self.assertTrue(result)
        finally:
            os.unlink(temp_file)

    def test_valid_override_file_invalid_file(self):
        """Test valid_override_file with an invalid override file."""

        # Create an override without required keys (missing Identifier and Input)
        override_dict = {
            "Description": "Invalid override",
            "ParentRecipe": "com.example.test.download",
        }

        with NamedTemporaryFile(mode="wb", suffix=".recipe", delete=False) as f:
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

        # Create a malformed plist file
        with NamedTemporaryFile(mode="w", suffix=".recipe", delete=False) as f:
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

        # Create a temporary recipe file
        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.testapp.download",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        # Create a temporary directory and recipe file
        recipe_file = os.path.join(self.tmp_dir.name, "TestApp.download.recipe")
        with open(recipe_file, "wb") as f:
            plistlib.dump(recipe_dict, f)

        result = autopkg.find_recipe_by_name("TestApp.download", [self.tmp_dir.name])
        self.assertEqual(result, recipe_file)

    def test_find_recipe_by_name_without_extension(self):
        """Test find_recipe_by_name when recipe name is provided without extension."""

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.testapp.download",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        recipe_file = os.path.join(self.tmp_dir.name, "TestApp.download.recipe")
        with open(recipe_file, "wb") as f:
            plistlib.dump(recipe_dict, f)

        # Should find recipe even without .recipe extension
        result = autopkg.find_recipe_by_name("TestApp.download", [self.tmp_dir.name])
        self.assertEqual(result, recipe_file)

    def test_find_recipe_by_name_in_subdirectory(self):
        """Test find_recipe_by_name when recipe is in a subdirectory."""

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.testapp.download",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        subdir = os.path.join(self.tmp_dir.name, "apps")
        os.makedirs(subdir)
        recipe_file = os.path.join(subdir, "TestApp.download.recipe")
        with open(recipe_file, "wb") as f:
            plistlib.dump(recipe_dict, f)

        result = autopkg.find_recipe_by_name("TestApp.download", [self.tmp_dir.name])
        self.assertEqual(result, recipe_file)

    def test_find_recipe_by_name_nonexistent_recipe(self):
        """Test find_recipe_by_name when recipe doesn't exist."""

        result = autopkg.find_recipe_by_name(
            "NonExistent.download", [self.tmp_dir.name]
        )
        self.assertIsNone(result)

    def test_find_recipe_by_name_invalid_recipe(self):
        """Test find_recipe_by_name when recipe file exists but is invalid."""

        # Create an invalid recipe file (missing required keys)
        invalid_recipe_file = os.path.join(self.tmp_dir.name, "Invalid.download.recipe")
        with open(invalid_recipe_file, "w") as f:
            f.write("This is not a valid plist")

        result = autopkg.find_recipe_by_name("Invalid.download", [self.tmp_dir.name])
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

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.testapp.download",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        recipe_file = os.path.join(self.tmp_dir.name, "TestApp.download.recipe")
        with open(recipe_file, "wb") as f:
            plistlib.dump(recipe_dict, f)

        # Mock find_recipe_by_identifier to return our test file
        original_find_by_id = autopkg.find_recipe_by_identifier
        autopkg.find_recipe_by_identifier = lambda id_name, dirs: (
            recipe_file if id_name == "com.example.testapp.download" else None
        )

        try:
            result = autopkg.find_recipe(
                "com.example.testapp.download", [self.tmp_dir.name]
            )
            self.assertEqual(result, recipe_file)
        finally:
            autopkg.find_recipe_by_identifier = original_find_by_id

    def test_find_recipe_finds_by_name(self):
        """Test find_recipe when recipe can be found by name but not identifier."""

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.testapp.download",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        recipe_file = os.path.join(self.tmp_dir.name, "TestApp.download.recipe")
        with open(recipe_file, "wb") as f:
            plistlib.dump(recipe_dict, f)

        # Mock find_recipe_by_identifier to return None
        original_find_by_id = autopkg.find_recipe_by_identifier
        autopkg.find_recipe_by_identifier = lambda id_name, dirs: None

        try:
            result = autopkg.find_recipe("TestApp.download", [self.tmp_dir.name])
            self.assertEqual(result, recipe_file)
        finally:
            autopkg.find_recipe_by_identifier = original_find_by_id

    def test_find_recipe_not_found(self):
        """Test find_recipe when recipe cannot be found by identifier or name."""

        # Mock find_recipe_by_identifier to return None
        original_find_by_id = autopkg.find_recipe_by_identifier
        autopkg.find_recipe_by_identifier = lambda id_name, dirs: None

        try:
            result = autopkg.find_recipe("NonExistent.download", [self.tmp_dir.name])
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

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        with NamedTemporaryFile(mode="wb", suffix=".recipe", delete=False) as f:
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

        recipe_dict = {
            "Description": "Test override",
            "Identifier": "com.example.test.override",
            "Input": {"NAME": "TestApp"},
            "ParentRecipe": "com.example.test",
        }

        recipe_file = os.path.join(self.tmp_dir.name, "TestApp.recipe")
        with open(recipe_file, "wb") as f:
            plistlib.dump(recipe_dict, f)

        result = autopkg.locate_recipe(
            "TestApp",
            [self.tmp_dir.name],
            [],
            make_suggestions=False,
            search_github=False,
        )
        self.assertEqual(result, recipe_file)

    def test_locate_recipe_search_recipe_dirs(self):
        """Test locate_recipe searching in recipe directories."""

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        recipe_file = os.path.join(self.tmp_dir.name, "TestApp.recipe")
        with open(recipe_file, "wb") as f:
            plistlib.dump(recipe_dict, f)

        result = autopkg.locate_recipe(
            "TestApp",
            [],
            [self.tmp_dir.name],
            make_suggestions=False,
            search_github=False,
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

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        subdir = os.path.join(self.tmp_dir.name, "subdir")
        os.makedirs(subdir)
        recipe_file = os.path.join(subdir, "TestApp.recipe")
        with open(recipe_file, "wb") as f:
            plistlib.dump(recipe_dict, f)

        result = autopkg.locate_recipe(
            "TestApp",
            [],
            [self.tmp_dir.name],
            make_suggestions=False,
            search_github=False,
        )
        self.assertEqual(result, recipe_file)

    # Tests for load_recipe function
    def test_load_recipe_simple_recipe(self):
        """Test load_recipe with a simple recipe file."""

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

        recipe_file = os.path.join(self.tmp_dir.name, "TestApp.recipe")
        with open(recipe_file, "wb") as f:
            plistlib.dump(recipe_dict, f)

        result = autopkg.load_recipe(
            "TestApp",
            [],
            [self.tmp_dir.name],
            make_suggestions=False,
            search_github=False,
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

        # Create parent recipe
        parent_file = os.path.join(self.tmp_dir.name, "Parent.recipe")
        with open(parent_file, "wb") as f:
            plistlib.dump(parent_recipe_dict, f)

        # Create child override in same directory
        child_file = os.path.join(self.tmp_dir.name, "Child.recipe")
        with open(child_file, "wb") as f:
            plistlib.dump(child_recipe_dict, f)

        result = autopkg.load_recipe(
            "Child",
            [],
            [self.tmp_dir.name],
            make_suggestions=False,
            search_github=False,
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

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        recipe_file = os.path.join(self.tmp_dir.name, "TestApp.recipe")
        with open(recipe_file, "wb") as f:
            plistlib.dump(recipe_dict, f)

        result = autopkg.load_recipe(
            "TestApp",
            [],
            [self.tmp_dir.name],
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

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        recipe_file = os.path.join(self.tmp_dir.name, "TestApp.recipe")
        with open(recipe_file, "wb") as f:
            plistlib.dump(recipe_dict, f)

        result = autopkg.load_recipe(
            "TestApp",
            [],
            [self.tmp_dir.name],
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

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "Input": {"NAME": "TestApp"},
            "Process": [
                {"Processor": "URLDownloader"},
                {"Processor": "CodeSignatureVerifier"},
            ],
        }

        recipe_file = os.path.join(self.tmp_dir.name, "TestApp.recipe")
        with open(recipe_file, "wb") as f:
            plistlib.dump(recipe_dict, f)

        result = autopkg.load_recipe(
            "TestApp",
            [],
            [self.tmp_dir.name],
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

        recipe_dict = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "Input": {"NAME": "TestApp"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        with NamedTemporaryFile(mode="wb", suffix=".recipe", delete=False) as f:
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

        # Create parent recipe
        parent_file = os.path.join(self.tmp_dir.name, "Parent.recipe")
        with open(parent_file, "wb") as f:
            plistlib.dump(parent_recipe_dict, f)

        # Create override directory
        override_dir = os.path.join(self.tmp_dir.name, "overrides")
        os.makedirs(override_dir)
        override_file = os.path.join(override_dir, "Override.recipe")
        with open(override_file, "wb") as f:
            plistlib.dump(override_dict, f)

        result = autopkg.load_recipe(
            "Override",
            [override_dir],
            [self.tmp_dir.name],
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

        # Create parent recipe
        parent_file = os.path.join(self.tmp_dir.name, "Parent.recipe")
        with open(parent_file, "wb") as f:
            plistlib.dump(parent_recipe_dict, f)

        # Create child override
        child_file = os.path.join(self.tmp_dir.name, "Child.recipe")
        with open(child_file, "wb") as f:
            plistlib.dump(child_recipe_dict, f)

        result = autopkg.load_recipe(
            "Child",
            [],
            [self.tmp_dir.name],
            make_suggestions=False,
            search_github=False,
        )

        self.assertIsNotNone(result)
        # Should use higher MinimumVersion from child
        self.assertEqual(result["MinimumVersion"], "2.5")

    def test_load_recipe_missing_minimum_version(self):
        """Test load_recipe when MinimumVersion is missing from recipes."""

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

        # Create parent recipe
        parent_file = os.path.join(self.tmp_dir.name, "Parent.recipe")
        with open(parent_file, "wb") as f:
            plistlib.dump(parent_recipe_dict, f)

        # Create child override
        child_file = os.path.join(self.tmp_dir.name, "Child.recipe")
        with open(child_file, "wb") as f:
            plistlib.dump(child_recipe_dict, f)

        result = autopkg.load_recipe(
            "Child",
            [],
            [self.tmp_dir.name],
            make_suggestions=False,
            search_github=False,
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

        with (
            patch.object(autopkg, "gen_common_parser") as mock_parser_gen,
            patch.object(autopkg, "add_search_and_override_dir_options"),
            patch.object(autopkg, "common_parse") as mock_parse,
            patch.object(autopkg, "get_override_dirs") as mock_get_override_dirs,
            patch.object(autopkg, "get_search_dirs") as mock_get_search_dirs,
            patch.object(autopkg, "load_recipe") as mock_load_recipe,
            patch.object(autopkg, "find_http_urls_in_recipe") as mock_find_urls,
            patch.object(autopkg, "core_processor_names") as mock_core_processors,
            patch.object(autopkg, "log") as mock_log,
        ):

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

        with (
            patch.object(autopkg, "gen_common_parser") as mock_parser_gen,
            patch.object(autopkg, "add_search_and_override_dir_options"),
            patch.object(autopkg, "common_parse") as mock_parse,
            patch.object(autopkg, "get_override_dirs") as mock_get_override_dirs,
            patch.object(autopkg, "get_search_dirs") as mock_get_search_dirs,
            patch.object(autopkg, "load_recipe") as mock_load_recipe,
            patch.object(autopkg, "find_http_urls_in_recipe") as mock_find_urls,
            patch.object(autopkg, "core_processor_names") as mock_core_processors,
            patch.object(autopkg, "log") as mock_log,
        ):

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

        with (
            patch.object(autopkg, "gen_common_parser") as mock_parser_gen,
            patch.object(autopkg, "add_search_and_override_dir_options"),
            patch.object(autopkg, "common_parse") as mock_parse,
            patch.object(autopkg, "get_override_dirs") as mock_get_override_dirs,
            patch.object(autopkg, "get_search_dirs") as mock_get_search_dirs,
            patch.object(autopkg, "load_recipe") as mock_load_recipe,
            patch.object(autopkg, "find_http_urls_in_recipe") as mock_find_urls,
            patch.object(autopkg, "core_processor_names") as mock_core_processors,
            patch.object(autopkg, "printplist") as mock_printplist,
            patch.object(autopkg, "log") as mock_log,
        ):

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

        with (
            patch.object(autopkg, "gen_common_parser") as mock_parser_gen,
            patch.object(autopkg, "add_search_and_override_dir_options"),
            patch.object(autopkg, "common_parse") as mock_parse,
            patch.object(autopkg, "get_override_dirs") as mock_get_override_dirs,
            patch.object(autopkg, "get_search_dirs") as mock_get_search_dirs,
            patch.object(autopkg, "load_recipe") as mock_load_recipe,
            patch.object(autopkg, "find_http_urls_in_recipe") as mock_find_urls,
            patch.object(autopkg, "core_processor_names") as mock_core_processors,
            patch.object(autopkg, "log") as mock_log,
        ):

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

        with (
            patch.object(autopkg, "gen_common_parser") as mock_parser_gen,
            patch.object(autopkg, "add_search_and_override_dir_options"),
            patch.object(autopkg, "common_parse") as mock_parse,
            patch.object(autopkg, "get_override_dirs") as mock_get_override_dirs,
            patch.object(autopkg, "get_search_dirs") as mock_get_search_dirs,
            patch.object(autopkg, "load_recipe") as mock_load_recipe,
            patch.object(autopkg, "find_http_urls_in_recipe") as mock_find_urls,
            patch.object(autopkg, "core_processor_names") as mock_core_processors,
            patch.object(autopkg, "log") as mock_log,
        ):

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

        with (
            patch.object(autopkg, "gen_common_parser") as mock_parser_gen,
            patch.object(autopkg, "add_search_and_override_dir_options"),
            patch.object(autopkg, "common_parse") as mock_parse,
            patch.object(autopkg, "get_override_dirs") as mock_get_override_dirs,
            patch.object(autopkg, "get_search_dirs") as mock_get_search_dirs,
            patch.object(autopkg, "load_recipe") as mock_load_recipe,
            patch.object(autopkg, "find_http_urls_in_recipe") as mock_find_urls,
            patch.object(autopkg, "core_processor_names") as mock_core_processors,
            patch("builtins.print") as mock_print,
        ):

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

        with (
            patch.object(autopkg, "gen_common_parser") as mock_parser_gen,
            patch.object(autopkg, "add_search_and_override_dir_options"),
            patch.object(autopkg, "common_parse") as mock_parse,
            patch.object(autopkg, "get_override_dirs") as mock_get_override_dirs,
            patch.object(autopkg, "get_search_dirs") as mock_get_search_dirs,
            patch.object(autopkg, "parse_recipe_list") as mock_parse_recipe_list,
            patch.object(autopkg, "load_recipe") as mock_load_recipe,
            patch.object(autopkg, "find_http_urls_in_recipe") as mock_find_urls,
            patch.object(autopkg, "core_processor_names") as mock_core_processors,
            patch("sys.stdout", new_callable=StringIO),
        ):

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
        with (
            patch.object(autopkg, "gen_common_parser") as mock_parser_gen,
            patch.object(autopkg, "add_search_and_override_dir_options"),
            patch.object(autopkg, "common_parse") as mock_parse,
            patch.object(autopkg, "get_override_dirs") as mock_get_override_dirs,
            patch.object(autopkg, "get_search_dirs") as mock_get_search_dirs,
            patch.object(autopkg, "log_err") as mock_log_err,
        ):

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
        with (
            patch.object(autopkg, "gen_common_parser") as mock_parser_gen,
            patch.object(autopkg, "add_search_and_override_dir_options"),
            patch.object(autopkg, "common_parse") as mock_parse,
            patch.object(autopkg, "get_override_dirs") as mock_get_override_dirs,
            patch.object(autopkg, "get_search_dirs") as mock_get_search_dirs,
            patch.object(autopkg, "load_recipe") as mock_load_recipe,
            patch.object(autopkg, "log_err") as mock_log_err,
        ):

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
        with (
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_recipe_list") as mock_get_recipe_list,
            patch("builtins.print") as mock_print,
        ):

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
        with (
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_recipe_list") as mock_get_recipe_list,
            patch("builtins.print") as mock_print,
        ):

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
        with (
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_recipe_list") as mock_get_recipe_list,
            patch("builtins.print") as mock_print,
            patch.dict("os.environ", {"HOME": "/Users/testuser"}),
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
        with (
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_recipe_list") as mock_get_recipe_list,
            patch("builtins.print") as mock_print,
            patch("plistlib.dumps") as mock_dumps,
        ):

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
        with (
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_recipe_list") as mock_get_recipe_list,
            patch("builtins.print"),
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
        with (
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.log_err") as mock_log_err,
        ):

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
        with (
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.log_err") as mock_log_err,
        ):

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
        with (
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.log_err") as mock_log_err,
        ):

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
        with (
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_recipe_list") as mock_get_recipe_list,
            patch("builtins.print") as mock_print,
            patch.dict("os.environ", {"HOME": "/Users/testuser"}),
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
        with (
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_recipe_list") as mock_get_recipe_list,
            patch("builtins.print") as mock_print,
        ):

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
        with (
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_recipe_list") as mock_get_recipe_list,
            patch("builtins.print"),
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
        with (
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_recipe_list") as mock_get_recipe_list,
            patch("builtins.print") as mock_print,
        ):

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
        with (
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_recipe_list") as mock_get_recipe_list,
            patch("builtins.print") as mock_print,
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
        with (
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_recipe_list") as mock_get_recipe_list,
            patch("builtins.print") as mock_print,
        ):

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
        with (
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_recipe_list") as mock_get_recipe_list,
            patch("builtins.print") as mock_print,
        ):

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

    def test_get_recipe_info_recipe_found_basic(self):
        """Test get_recipe_info when recipe is found with basic information."""
        recipe_name = "TestRecipe"
        override_dirs = ["/overrides"]
        recipe_dirs = ["/recipes"]

        mock_recipe = {
            "Description": "Test recipe for testing",
            "Identifier": "com.example.test",
            "RECIPE_PATH": "/path/to/TestRecipe.recipe",
            "Input": {"NAME": "TestApp", "VERSION": "1.0"},
            "Process": [{"Processor": "URLDownloader"}],
        }

        with (
            patch("autopkg.load_recipe") as mock_load_recipe,
            patch("autopkg.log") as mock_log,
            patch("autopkg.get_identifier") as mock_get_identifier,
            patch("autopkg.has_munkiimporter_step") as mock_has_munki,
            patch("autopkg.has_check_phase") as mock_has_check,
            patch("autopkg.builds_a_package") as mock_builds_package,
        ):

            mock_load_recipe.return_value = mock_recipe
            mock_get_identifier.return_value = "com.example.test"
            mock_has_munki.return_value = False
            mock_has_check.return_value = False
            mock_builds_package.return_value = False

            result = autopkg.get_recipe_info(recipe_name, override_dirs, recipe_dirs)

            self.assertTrue(result)
            mock_load_recipe.assert_called_once_with(
                recipe_name,
                override_dirs,
                recipe_dirs,
                make_suggestions=True,
                search_github=True,
                auto_pull=False,
            )

            # Check that various log calls were made
            mock_log.assert_any_call("Description:         Test recipe for testing")
            mock_log.assert_any_call("Identifier:          com.example.test")
            mock_log.assert_any_call("Munki import recipe: False")
            mock_log.assert_any_call("Has check phase:     False")
            mock_log.assert_any_call("Builds package:      False")
            mock_log.assert_any_call("Recipe file path:    /path/to/TestRecipe.recipe")
            mock_log.assert_any_call("Input values: ")

    def test_get_recipe_info_recipe_not_found(self):
        """Test get_recipe_info when recipe is not found."""
        recipe_name = "NonExistentRecipe"
        override_dirs = ["/overrides"]
        recipe_dirs = ["/recipes"]

        with (
            patch("autopkg.load_recipe") as mock_load_recipe,
            patch("autopkg.log_err") as mock_log_err,
        ):

            mock_load_recipe.return_value = None  # Recipe not found

            result = autopkg.get_recipe_info(recipe_name, override_dirs, recipe_dirs)

            self.assertFalse(result)
            mock_load_recipe.assert_called_once_with(
                recipe_name,
                override_dirs,
                recipe_dirs,
                make_suggestions=True,
                search_github=True,
                auto_pull=False,
            )
            mock_log_err.assert_called_once_with(
                "No valid recipe found for NonExistentRecipe"
            )

    def test_get_recipe_info_with_multiline_description(self):
        """Test get_recipe_info with multiline description."""
        recipe_name = "TestRecipe"
        override_dirs = ["/overrides"]
        recipe_dirs = ["/recipes"]

        mock_recipe = {
            "Description": "Line 1 of description\nLine 2 of description\nLine 3 of description",
            "Identifier": "com.example.test",
            "RECIPE_PATH": "/path/to/TestRecipe.recipe",
            "Input": {},
            "Process": [],
        }

        with (
            patch("autopkg.load_recipe") as mock_load_recipe,
            patch("autopkg.log") as mock_log,
            patch("autopkg.get_identifier") as mock_get_identifier,
            patch("autopkg.has_munkiimporter_step") as mock_has_munki,
            patch("autopkg.has_check_phase") as mock_has_check,
            patch("autopkg.builds_a_package") as mock_builds_package,
        ):

            mock_load_recipe.return_value = mock_recipe
            mock_get_identifier.return_value = "com.example.test"
            mock_has_munki.return_value = False
            mock_has_check.return_value = False
            mock_builds_package.return_value = False

            result = autopkg.get_recipe_info(recipe_name, override_dirs, recipe_dirs)

            self.assertTrue(result)
            # Check that multiline description is properly formatted
            expected_description = (
                "Description:         Line 1 of description\n"
                "                     Line 2 of description\n"
                "                     Line 3 of description"
            )
            mock_log.assert_any_call(expected_description)

    def test_get_recipe_info_with_parent_recipes(self):
        """Test get_recipe_info with parent recipes."""
        recipe_name = "TestRecipe"
        override_dirs = ["/overrides"]
        recipe_dirs = ["/recipes"]

        mock_recipe = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "RECIPE_PATH": "/path/to/TestRecipe.recipe",
            "Input": {},
            "Process": [],
            "PARENT_RECIPES": [
                "/path/to/Parent1.recipe",
                "/path/to/Parent2.recipe",
            ],
        }

        with (
            patch("autopkg.load_recipe") as mock_load_recipe,
            patch("autopkg.log") as mock_log,
            patch("autopkg.get_identifier") as mock_get_identifier,
            patch("autopkg.has_munkiimporter_step") as mock_has_munki,
            patch("autopkg.has_check_phase") as mock_has_check,
            patch("autopkg.builds_a_package") as mock_builds_package,
        ):

            mock_load_recipe.return_value = mock_recipe
            mock_get_identifier.return_value = "com.example.test"
            mock_has_munki.return_value = False
            mock_has_check.return_value = False
            mock_builds_package.return_value = False

            result = autopkg.get_recipe_info(recipe_name, override_dirs, recipe_dirs)

            self.assertTrue(result)
            # Check that parent recipes are logged
            expected_parents = (
                "Parent recipe(s):    /path/to/Parent1.recipe\n"
                "                     /path/to/Parent2.recipe"
            )
            mock_log.assert_any_call(expected_parents)

    def test_get_recipe_info_with_munki_importer(self):
        """Test get_recipe_info with munki importer step."""
        recipe_name = "TestRecipe"
        override_dirs = ["/overrides"]
        recipe_dirs = ["/recipes"]

        mock_recipe = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "RECIPE_PATH": "/path/to/TestRecipe.recipe",
            "Input": {},
            "Process": [{"Processor": "MunkiImporter"}],
        }

        with (
            patch("autopkg.load_recipe") as mock_load_recipe,
            patch("autopkg.log") as mock_log,
            patch("autopkg.get_identifier") as mock_get_identifier,
            patch("autopkg.has_munkiimporter_step") as mock_has_munki,
            patch("autopkg.has_check_phase") as mock_has_check,
            patch("autopkg.builds_a_package") as mock_builds_package,
        ):

            mock_load_recipe.return_value = mock_recipe
            mock_get_identifier.return_value = "com.example.test"
            mock_has_munki.return_value = True  # Has MunkiImporter
            mock_has_check.return_value = False
            mock_builds_package.return_value = False

            result = autopkg.get_recipe_info(recipe_name, override_dirs, recipe_dirs)

            self.assertTrue(result)
            mock_log.assert_any_call("Munki import recipe: True")

    def test_get_recipe_info_with_check_phase(self):
        """Test get_recipe_info with check phase."""
        recipe_name = "TestRecipe"
        override_dirs = ["/overrides"]
        recipe_dirs = ["/recipes"]

        mock_recipe = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "RECIPE_PATH": "/path/to/TestRecipe.recipe",
            "Input": {},
            "Process": [{"Processor": "EndOfCheckPhase"}],
        }

        with (
            patch("autopkg.load_recipe") as mock_load_recipe,
            patch("autopkg.log") as mock_log,
            patch("autopkg.get_identifier") as mock_get_identifier,
            patch("autopkg.has_munkiimporter_step") as mock_has_munki,
            patch("autopkg.has_check_phase") as mock_has_check,
            patch("autopkg.builds_a_package") as mock_builds_package,
        ):

            mock_load_recipe.return_value = mock_recipe
            mock_get_identifier.return_value = "com.example.test"
            mock_has_munki.return_value = False
            mock_has_check.return_value = True  # Has check phase
            mock_builds_package.return_value = False

            result = autopkg.get_recipe_info(recipe_name, override_dirs, recipe_dirs)

            self.assertTrue(result)
            mock_log.assert_any_call("Has check phase:     True")

    def test_get_recipe_info_builds_package(self):
        """Test get_recipe_info that builds a package."""
        recipe_name = "TestRecipe"
        override_dirs = ["/overrides"]
        recipe_dirs = ["/recipes"]

        mock_recipe = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "RECIPE_PATH": "/path/to/TestRecipe.recipe",
            "Input": {},
            "Process": [{"Processor": "PkgCreator"}],
        }

        with (
            patch("autopkg.load_recipe") as mock_load_recipe,
            patch("autopkg.log") as mock_log,
            patch("autopkg.get_identifier") as mock_get_identifier,
            patch("autopkg.has_munkiimporter_step") as mock_has_munki,
            patch("autopkg.has_check_phase") as mock_has_check,
            patch("autopkg.builds_a_package") as mock_builds_package,
        ):

            mock_load_recipe.return_value = mock_recipe
            mock_get_identifier.return_value = "com.example.test"
            mock_has_munki.return_value = False
            mock_has_check.return_value = False
            mock_builds_package.return_value = True  # Builds package

            result = autopkg.get_recipe_info(recipe_name, override_dirs, recipe_dirs)

            self.assertTrue(result)
            mock_log.assert_any_call("Builds package:      True")

    def test_get_recipe_info_with_complex_input(self):
        """Test get_recipe_info with complex input dictionary."""
        recipe_name = "TestRecipe"
        override_dirs = ["/overrides"]
        recipe_dirs = ["/recipes"]

        mock_recipe = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "RECIPE_PATH": "/path/to/TestRecipe.recipe",
            "Input": {
                "NAME": "TestApp",
                "VERSION": "1.0",
                "NESTED": {"key1": "value1", "key2": ["item1", "item2"]},
            },
            "Process": [],
        }

        with (
            patch("autopkg.load_recipe") as mock_load_recipe,
            patch("autopkg.log") as mock_log,
            patch("autopkg.get_identifier") as mock_get_identifier,
            patch("autopkg.has_munkiimporter_step") as mock_has_munki,
            patch("autopkg.has_check_phase") as mock_has_check,
            patch("autopkg.builds_a_package") as mock_builds_package,
            patch("pprint.pformat") as mock_pformat,
        ):

            mock_load_recipe.return_value = mock_recipe
            mock_get_identifier.return_value = "com.example.test"
            mock_has_munki.return_value = False
            mock_has_check.return_value = False
            mock_builds_package.return_value = False
            mock_pformat.return_value = "{'formatted': 'input'}"

            result = autopkg.get_recipe_info(recipe_name, override_dirs, recipe_dirs)

            self.assertTrue(result)
            mock_log.assert_any_call("Input values: ")
            # Check that pprint.pformat was called with the Input dict
            mock_pformat.assert_called_once_with(mock_recipe["Input"], indent=4)

    def test_get_recipe_info_with_empty_description(self):
        """Test get_recipe_info with empty description."""
        recipe_name = "TestRecipe"
        override_dirs = ["/overrides"]
        recipe_dirs = ["/recipes"]

        mock_recipe = {
            "Description": "",  # Empty description
            "Identifier": "com.example.test",
            "RECIPE_PATH": "/path/to/TestRecipe.recipe",
            "Input": {},
            "Process": [],
        }

        with (
            patch("autopkg.load_recipe") as mock_load_recipe,
            patch("autopkg.log") as mock_log,
            patch("autopkg.get_identifier") as mock_get_identifier,
            patch("autopkg.has_munkiimporter_step") as mock_has_munki,
            patch("autopkg.has_check_phase") as mock_has_check,
            patch("autopkg.builds_a_package") as mock_builds_package,
        ):

            mock_load_recipe.return_value = mock_recipe
            mock_get_identifier.return_value = "com.example.test"
            mock_has_munki.return_value = False
            mock_has_check.return_value = False
            mock_builds_package.return_value = False

            result = autopkg.get_recipe_info(recipe_name, override_dirs, recipe_dirs)

            self.assertTrue(result)
            mock_log.assert_any_call("Description:         ")

    def test_get_recipe_info_with_missing_description(self):
        """Test get_recipe_info with missing description key."""
        recipe_name = "TestRecipe"
        override_dirs = ["/overrides"]
        recipe_dirs = ["/recipes"]

        mock_recipe = {
            # No Description key
            "Identifier": "com.example.test",
            "RECIPE_PATH": "/path/to/TestRecipe.recipe",
            "Input": {},
            "Process": [],
        }

        with (
            patch("autopkg.load_recipe") as mock_load_recipe,
            patch("autopkg.log") as mock_log,
            patch("autopkg.get_identifier") as mock_get_identifier,
            patch("autopkg.has_munkiimporter_step") as mock_has_munki,
            patch("autopkg.has_check_phase") as mock_has_check,
            patch("autopkg.builds_a_package") as mock_builds_package,
        ):

            mock_load_recipe.return_value = mock_recipe
            mock_get_identifier.return_value = "com.example.test"
            mock_has_munki.return_value = False
            mock_has_check.return_value = False
            mock_builds_package.return_value = False

            result = autopkg.get_recipe_info(recipe_name, override_dirs, recipe_dirs)

            self.assertTrue(result)
            mock_log.assert_any_call("Description:         ")

    def test_get_recipe_info_with_options(self):
        """Test get_recipe_info with different options."""
        recipe_name = "TestRecipe"
        override_dirs = ["/overrides"]
        recipe_dirs = ["/recipes"]

        mock_recipe = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "RECIPE_PATH": "/path/to/TestRecipe.recipe",
            "Input": {},
            "Process": [],
        }

        with (
            patch("autopkg.load_recipe") as mock_load_recipe,
            patch("autopkg.log"),
            patch("autopkg.get_identifier") as mock_get_identifier,
            patch("autopkg.has_munkiimporter_step") as mock_has_munki,
            patch("autopkg.has_check_phase") as mock_has_check,
            patch("autopkg.builds_a_package") as mock_builds_package,
        ):

            mock_load_recipe.return_value = mock_recipe
            mock_get_identifier.return_value = "com.example.test"
            mock_has_munki.return_value = False
            mock_has_check.return_value = False
            mock_builds_package.return_value = False

            result = autopkg.get_recipe_info(
                recipe_name,
                override_dirs,
                recipe_dirs,
                make_suggestions=False,
                search_github=False,
                auto_pull=True,
            )

            self.assertTrue(result)
            mock_load_recipe.assert_called_once_with(
                recipe_name,
                override_dirs,
                recipe_dirs,
                make_suggestions=False,
                search_github=False,
                auto_pull=True,
            )

    def test_get_recipe_info_no_parent_recipes(self):
        """Test get_recipe_info when PARENT_RECIPES is not present."""
        recipe_name = "TestRecipe"
        override_dirs = ["/overrides"]
        recipe_dirs = ["/recipes"]

        mock_recipe = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "RECIPE_PATH": "/path/to/TestRecipe.recipe",
            "Input": {},
            "Process": [],
            # No PARENT_RECIPES key
        }

        with (
            patch("autopkg.load_recipe") as mock_load_recipe,
            patch("autopkg.log") as mock_log,
            patch("autopkg.get_identifier") as mock_get_identifier,
            patch("autopkg.has_munkiimporter_step") as mock_has_munki,
            patch("autopkg.has_check_phase") as mock_has_check,
            patch("autopkg.builds_a_package") as mock_builds_package,
        ):

            mock_load_recipe.return_value = mock_recipe
            mock_get_identifier.return_value = "com.example.test"
            mock_has_munki.return_value = False
            mock_has_check.return_value = False
            mock_builds_package.return_value = False

            result = autopkg.get_recipe_info(recipe_name, override_dirs, recipe_dirs)

            self.assertTrue(result)
            # Should not log parent recipes section
            parent_calls = [
                call
                for call in mock_log.call_args_list
                if "Parent recipe(s)" in str(call)
            ]
            self.assertEqual(len(parent_calls), 0)

    def test_get_recipe_info_empty_input(self):
        """Test get_recipe_info with empty Input dictionary."""
        recipe_name = "TestRecipe"
        override_dirs = ["/overrides"]
        recipe_dirs = ["/recipes"]

        mock_recipe = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "RECIPE_PATH": "/path/to/TestRecipe.recipe",
            "Input": {},  # Empty input
            "Process": [],
        }

        with (
            patch("autopkg.load_recipe") as mock_load_recipe,
            patch("autopkg.log") as mock_log,
            patch("autopkg.get_identifier") as mock_get_identifier,
            patch("autopkg.has_munkiimporter_step") as mock_has_munki,
            patch("autopkg.has_check_phase") as mock_has_check,
            patch("autopkg.builds_a_package") as mock_builds_package,
            patch("pprint.pformat") as mock_pformat,
        ):

            mock_load_recipe.return_value = mock_recipe
            mock_get_identifier.return_value = "com.example.test"
            mock_has_munki.return_value = False
            mock_has_check.return_value = False
            mock_builds_package.return_value = False
            mock_pformat.return_value = "{}"

            result = autopkg.get_recipe_info(recipe_name, override_dirs, recipe_dirs)

            self.assertTrue(result)
            mock_log.assert_any_call("Input values: ")
            mock_pformat.assert_called_once_with({}, indent=4)

    def test_get_recipe_list_no_directories_provided(self):
        """Test get_recipe_list when no directories are provided."""
        with (
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("os.path.isdir") as mock_isdir,
            patch("glob.glob") as mock_glob,
        ):

            mock_get_override_dirs.return_value = ["/default/overrides"]
            mock_get_search_dirs.return_value = ["/default/recipes"]
            mock_isdir.return_value = False  # No directories exist
            mock_glob.return_value = []

            result = autopkg.get_recipe_list()

            # Should return empty list when no directories exist
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 0)

            # Should call default directory functions
            mock_get_override_dirs.assert_called_once()
            mock_get_search_dirs.assert_called_once()

    def test_get_recipe_list_augmented_list_option(self):
        """Test get_recipe_list with augmented_list=True."""
        override_dirs = ["/overrides"]
        search_dirs = ["/recipes"]

        # Mock a recipe and its override with same name and matching parent
        mock_recipe = {
            "Description": "Download TestApp",
            "Identifier": "com.test.download",
            "Input": {},
            "Process": [],
        }
        mock_override = {
            "ParentRecipe": "com.test.download",
            "Input": {"NAME": "CustomTestApp"},
        }

        with (
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("os.path.isdir") as mock_isdir,
            patch("glob.glob") as mock_glob,
            patch("autopkg.recipe_from_file") as mock_recipe_from_file,
            patch("autopkg.valid_recipe_dict") as mock_valid_recipe,
            patch("autopkg.valid_override_dict") as mock_valid_override,
            patch("autopkg.get_identifier") as mock_get_identifier,
            patch("autopkg.remove_recipe_extension") as mock_remove_ext,
            patch("os.path.basename") as mock_basename,
        ):

            mock_get_override_dirs.return_value = override_dirs
            mock_get_search_dirs.return_value = search_dirs
            mock_isdir.return_value = True

            def glob_side_effect(pattern):
                if "/recipes/" in pattern:
                    return ["/recipes/TestApp.recipe"]
                elif "/overrides/" in pattern:
                    return ["/overrides/TestApp.recipe"]
                return []

            mock_glob.side_effect = glob_side_effect

            def recipe_from_file_side_effect(path):
                if "/recipes/" in path:
                    return mock_recipe.copy()
                elif "/overrides/" in path:
                    return mock_override.copy()
                return {}

            mock_recipe_from_file.side_effect = recipe_from_file_side_effect
            mock_valid_recipe.return_value = True
            mock_valid_override.return_value = True
            mock_get_identifier.return_value = None
            mock_remove_ext.return_value = "TestApp"
            mock_basename.return_value = "TestApp.recipe"

            result = autopkg.get_recipe_list(
                override_dirs, search_dirs, augmented_list=True, show_all=False
            )

            # With augmented_list=True and show_all=False,
            # the parent recipe should be removed when override has same name
            self.assertIsInstance(result, list)

            # Check that IsOverride flag is set for overrides
            override_items = [item for item in result if item.get("IsOverride")]
            self.assertGreater(len(override_items), 0)

    def test_get_recipe_list_show_all_option(self):
        """Test get_recipe_list with show_all=True."""
        override_dirs = ["/overrides"]
        search_dirs = ["/recipes"]

        mock_recipe = {
            "Description": "Download TestApp",
            "Identifier": "com.test.download",
            "Input": {},
            "Process": [],
        }
        mock_override = {
            "ParentRecipe": "com.test.download",
            "Input": {"NAME": "CustomTestApp"},
        }

        with (
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("os.path.isdir") as mock_isdir,
            patch("glob.glob") as mock_glob,
            patch("autopkg.recipe_from_file") as mock_recipe_from_file,
            patch("autopkg.valid_recipe_dict") as mock_valid_recipe,
            patch("autopkg.valid_override_dict") as mock_valid_override,
            patch("autopkg.get_identifier") as mock_get_identifier,
            patch("autopkg.remove_recipe_extension") as mock_remove_ext,
            patch("os.path.basename") as mock_basename,
        ):

            mock_get_override_dirs.return_value = override_dirs
            mock_get_search_dirs.return_value = search_dirs
            mock_isdir.return_value = True

            def glob_side_effect(pattern):
                if "/recipes/" in pattern:
                    return ["/recipes/TestApp.recipe"]
                elif "/overrides/" in pattern:
                    return ["/overrides/TestApp.recipe"]
                return []

            mock_glob.side_effect = glob_side_effect

            def recipe_from_file_side_effect(path):
                if "/recipes/" in path:
                    return mock_recipe.copy()
                elif "/overrides/" in path:
                    return mock_override.copy()
                return {}

            mock_recipe_from_file.side_effect = recipe_from_file_side_effect
            mock_valid_recipe.return_value = True
            mock_valid_override.return_value = True
            mock_get_identifier.return_value = None
            mock_remove_ext.return_value = "TestApp"
            mock_basename.return_value = "TestApp.recipe"

            result = autopkg.get_recipe_list(
                override_dirs, search_dirs, augmented_list=True, show_all=True
            )

            # With show_all=True, both recipe and override should be in the list
            self.assertIsInstance(result, list)

    def test_get_recipe_list_invalid_recipe(self):
        """Test get_recipe_list with invalid recipe files."""
        override_dirs = ["/overrides"]
        search_dirs = ["/recipes"]

        with (
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("os.path.isdir") as mock_isdir,
            patch("glob.glob") as mock_glob,
            patch("autopkg.recipe_from_file") as mock_recipe_from_file,
            patch("autopkg.valid_recipe_dict") as mock_valid_recipe,
            patch("autopkg.valid_override_dict") as mock_valid_override,
        ):

            mock_get_override_dirs.return_value = override_dirs
            mock_get_search_dirs.return_value = search_dirs
            mock_isdir.return_value = True
            mock_glob.return_value = ["/recipes/BadRecipe.recipe"]
            mock_recipe_from_file.return_value = {"bad": "recipe"}
            mock_valid_recipe.return_value = False  # Invalid recipe
            mock_valid_override.return_value = False

            result = autopkg.get_recipe_list(override_dirs, search_dirs)

            # Should return empty list when all recipes are invalid
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 0)

    def test_get_recipe_list_with_identifier_from_input(self):
        """Test get_recipe_list when recipe has Identifier in Input section."""
        override_dirs = []
        search_dirs = ["/recipes"]

        mock_recipe = {
            "Description": "Test recipe",
            "Input": {"IDENTIFIER": "com.test.from.input"},
            "Process": [],
            # No top-level Identifier
        }

        with (
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("os.path.isdir") as mock_isdir,
            patch("glob.glob") as mock_glob,
            patch("autopkg.recipe_from_file") as mock_recipe_from_file,
            patch("autopkg.valid_recipe_dict") as mock_valid_recipe,
            patch("autopkg.valid_override_dict") as mock_valid_override,
            patch("autopkg.get_identifier") as mock_get_identifier,
            patch("autopkg.remove_recipe_extension") as mock_remove_ext,
            patch("os.path.basename") as mock_basename,
        ):

            mock_get_override_dirs.return_value = []
            mock_get_search_dirs.return_value = search_dirs
            mock_isdir.return_value = True
            mock_glob.return_value = ["/recipes/TestApp.recipe"]
            mock_recipe_from_file.return_value = mock_recipe.copy()
            mock_valid_recipe.return_value = True
            mock_valid_override.return_value = False
            mock_get_identifier.return_value = "com.test.from.input"
            mock_remove_ext.return_value = "TestApp"
            mock_basename.return_value = "TestApp.recipe"

            result = autopkg.get_recipe_list(override_dirs, search_dirs)

            # Should add Identifier from Input to top level
            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)

            # Check that get_identifier was called to extract identifier
            mock_get_identifier.assert_called()

    def test_get_recipe_list_nonexistent_directories(self):
        """Test get_recipe_list with nonexistent directories."""
        override_dirs = ["/nonexistent/overrides"]
        search_dirs = ["/nonexistent/recipes"]

        with patch("os.path.isdir") as mock_isdir, patch("glob.glob") as mock_glob:

            mock_isdir.return_value = False  # Directories don't exist

            result = autopkg.get_recipe_list(override_dirs, search_dirs)

            # Should return empty list when directories don't exist
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 0)

            # glob should not be called for nonexistent directories
            mock_glob.assert_not_called()

    def test_find_http_urls_in_recipe_empty_recipe(self):
        """Test find_http_urls_in_recipe with an empty recipe."""
        recipe = {}
        result = autopkg.find_http_urls_in_recipe(recipe)
        self.assertEqual(result, {})

    def test_find_http_urls_in_recipe_no_urls(self):
        """Test find_http_urls_in_recipe with a recipe containing no HTTP URLs."""
        recipe = {
            "Input": {
                "NAME": "TestApp",
                "VERSION": "1.0",
                "HTTPS_URL": "https://example.com/download",  # HTTPS, not HTTP
            },
            "Process": [
                {
                    "Processor": "URLDownloader",
                    "Arguments": {
                        "url": "https://secure.example.com/file.dmg",
                        "filename": "test.dmg",
                    },
                }
            ],
        }
        result = autopkg.find_http_urls_in_recipe(recipe)
        self.assertEqual(result, {})

    def test_find_http_urls_in_recipe_input_section_only(self):
        """Test find_http_urls_in_recipe with HTTP URLs only in Input section."""
        recipe = {
            "Input": {
                "NAME": "TestApp",
                "DOWNLOAD_URL": "http://example.com/download",
                "MIRROR_URL": "http://mirror.example.com/file.zip",
            }
        }
        result = autopkg.find_http_urls_in_recipe(recipe)
        expected = {
            "Input": {
                "DOWNLOAD_URL": "http://example.com/download",
                "MIRROR_URL": "http://mirror.example.com/file.zip",
            }
        }
        self.assertEqual(result, expected)

    def test_find_http_urls_in_recipe_process_section_only(self):
        """Test find_http_urls_in_recipe with HTTP URLs only in Process section."""
        recipe = {
            "Process": [
                {
                    "Processor": "URLDownloader",
                    "Arguments": {
                        "url": "http://example.com/file.dmg",
                        "filename": "test.dmg",
                    },
                },
                {
                    "Processor": "CURLTextSearcher",
                    "Arguments": {
                        "url": "http://api.example.com/version",
                        "re_pattern": r"version:\s*(\d+\.\d+)",
                    },
                },
            ]
        }
        result = autopkg.find_http_urls_in_recipe(recipe)
        expected = {
            "Process": {
                "URLDownloader": {"url": "http://example.com/file.dmg"},
                "CURLTextSearcher": {"url": "http://api.example.com/version"},
            }
        }
        self.assertEqual(result, expected)

    def test_find_http_urls_in_recipe_both_sections(self):
        """Test find_http_urls_in_recipe with HTTP URLs in both Input and Process sections."""
        recipe = {
            "Input": {
                "BASE_URL": "http://downloads.example.com",
                "APP_NAME": "TestApp",
            },
            "Process": [
                {
                    "Processor": "URLDownloader",
                    "Arguments": {
                        "url": "http://example.com/file.dmg",
                        "filename": "test.dmg",
                    },
                }
            ],
        }
        result = autopkg.find_http_urls_in_recipe(recipe)
        expected = {
            "Input": {"BASE_URL": "http://downloads.example.com"},
            "Process": {"URLDownloader": {"url": "http://example.com/file.dmg"}},
        }
        self.assertEqual(result, expected)

    def test_find_http_urls_in_recipe_multiple_processors_same_type(self):
        """Test find_http_urls_in_recipe with multiple processors of the same type."""
        recipe = {
            "Process": [
                {
                    "Processor": "URLDownloader",
                    "Arguments": {
                        "url": "http://example.com/file1.dmg",
                        "filename": "test1.dmg",
                    },
                },
                {
                    "Processor": "URLDownloader",
                    "Arguments": {
                        "url": "http://example.com/file2.dmg",
                        "filename": "test2.dmg",
                    },
                },
            ]
        }
        result = autopkg.find_http_urls_in_recipe(recipe)
        # Note: The function appears to overwrite previous entries for the same processor
        # This is based on the implementation using dict assignment
        expected = {
            "Process": {"URLDownloader": {"url": "http://example.com/file2.dmg"}}
        }
        self.assertEqual(result, expected)

    def test_find_http_urls_in_recipe_non_string_values(self):
        """Test find_http_urls_in_recipe with non-string values that shouldn't be processed."""
        recipe = {
            "Input": {
                "URL": "http://example.com/download",
                "PORT": 8080,  # Integer
                "ENABLED": True,  # Boolean
                "CONFIG": {"key": "value"},  # Dict
            },
            "Process": [
                {
                    "Processor": "URLDownloader",
                    "Arguments": {
                        "url": "http://example.com/file.dmg",
                        "timeout": 30,  # Integer
                        "retries": 3,  # Integer
                    },
                }
            ],
        }
        result = autopkg.find_http_urls_in_recipe(recipe)
        expected = {
            "Input": {"URL": "http://example.com/download"},
            "Process": {"URLDownloader": {"url": "http://example.com/file.dmg"}},
        }
        self.assertEqual(result, expected)

    def test_find_http_urls_in_recipe_missing_arguments(self):
        """Test find_http_urls_in_recipe with processors missing Arguments section."""
        recipe = {
            "Process": [
                {
                    "Processor": "AppDmgVersioner"
                    # No Arguments section
                },
                {
                    "Processor": "URLDownloader",
                    "Arguments": {"url": "http://example.com/file.dmg"},
                },
            ]
        }
        result = autopkg.find_http_urls_in_recipe(recipe)
        expected = {
            "Process": {"URLDownloader": {"url": "http://example.com/file.dmg"}}
        }
        self.assertEqual(result, expected)

    def test_find_http_urls_in_recipe_empty_sections(self):
        """Test find_http_urls_in_recipe with empty Input and Process sections."""
        recipe = {"Input": {}, "Process": []}
        result = autopkg.find_http_urls_in_recipe(recipe)
        self.assertEqual(result, {})

    def test_find_http_urls_in_recipe_http_prefix_check(self):
        """Test find_http_urls_in_recipe only catches URLs starting with 'http:'."""
        recipe = {
            "Input": {
                "HTTP_URL": "http://example.com/download",
                "HTTPS_URL": "https://example.com/secure",
                "FTP_URL": "ftp://example.com/file",
                "FILE_URL": "file:///path/to/file",
                "PARTIAL_HTTP": "prefix_http://example.com",
                "NOT_URL": "this is not a URL",
            }
        }
        result = autopkg.find_http_urls_in_recipe(recipe)
        expected = {"Input": {"HTTP_URL": "http://example.com/download"}}
        self.assertEqual(result, expected)

    def test_new_recipe_basic_plist(self):
        """Test new_recipe creates a basic plist recipe."""
        argv = ["autopkg", "new-recipe", "test.recipe"]

        with (
            patch("autopkg.common_parse") as mock_parse,
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("builtins.open", unittest.mock.mock_open()) as mock_file,
            patch("autopkg.plistlib.dump") as mock_plist_dump,
            patch("autopkg.log") as mock_log,
            patch("autopkg.plist_serializer") as mock_serializer,
        ):

            # Mock parser setup
            mock_parser_obj = unittest.mock.Mock()
            mock_parser.return_value = mock_parser_obj

            # Mock options
            mock_options = unittest.mock.Mock()
            mock_options.identifier = None
            mock_options.parent_identifier = None
            mock_options.format = "plist"

            mock_parse.return_value = (mock_options, ["test.recipe"])
            mock_serializer.return_value = {"serialized": "recipe"}

            autopkg.new_recipe(argv)

            # Verify parser setup
            mock_parser_obj.add_option.assert_any_call(
                "-i", "--identifier", help="Recipe identifier"
            )
            mock_parser_obj.add_option.assert_any_call(
                "-p",
                "--parent-identifier",
                help="Parent recipe identifier for this recipe.",
            )

            # Verify file operations
            mock_file.assert_called_once_with("test.recipe", "wb")
            mock_plist_dump.assert_called_once()
            mock_log.assert_called_with("Saved new recipe to test.recipe")

    def test_new_recipe_with_identifier(self):
        """Test new_recipe with custom identifier."""
        argv = ["autopkg", "new-recipe", "custom.recipe"]

        with (
            patch("autopkg.common_parse") as mock_parse,
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("builtins.open", unittest.mock.mock_open()) as _,
            patch("autopkg.plistlib.dump") as _,
            patch("autopkg.log") as _,
            patch("autopkg.plist_serializer") as mock_serializer,
        ):

            mock_parser_obj = unittest.mock.Mock()
            mock_parser.return_value = mock_parser_obj

            mock_options = unittest.mock.Mock()
            mock_options.identifier = "com.example.custom"
            mock_options.parent_identifier = None
            mock_options.format = "plist"

            mock_parse.return_value = (mock_options, ["custom.recipe"])
            mock_serializer.return_value = {"serialized": "recipe"}

            autopkg.new_recipe(argv)

            # Check that plist_serializer was called with recipe containing custom identifier
            args, kwargs = mock_serializer.call_args
            recipe = args[0]
            self.assertEqual(recipe["Identifier"], "com.example.custom")

    def test_new_recipe_with_parent(self):
        """Test new_recipe with parent recipe identifier."""
        argv = ["autopkg", "new-recipe", "child.recipe"]

        with (
            patch("autopkg.common_parse") as mock_parse,
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("builtins.open", unittest.mock.mock_open()) as _,
            patch("autopkg.plistlib.dump") as _,
            patch("autopkg.log") as _,
            patch("autopkg.plist_serializer") as mock_serializer,
        ):

            mock_parser_obj = unittest.mock.Mock()
            mock_parser.return_value = mock_parser_obj

            mock_options = unittest.mock.Mock()
            mock_options.identifier = None
            mock_options.parent_identifier = "com.example.parent"
            mock_options.format = "plist"

            mock_parse.return_value = (mock_options, ["child.recipe"])
            mock_serializer.return_value = {"serialized": "recipe"}

            autopkg.new_recipe(argv)

            # Check that plist_serializer was called with recipe containing parent
            args, kwargs = mock_serializer.call_args
            recipe = args[0]
            self.assertEqual(recipe["ParentRecipe"], "com.example.parent")

    def test_new_recipe_yaml_format(self):
        """Test new_recipe creates YAML format recipe."""
        argv = ["autopkg", "new-recipe", "test.recipe.yaml"]

        with (
            patch("autopkg.common_parse") as mock_parse,
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("builtins.open", unittest.mock.mock_open()) as _,
            patch("autopkg.yaml.dump") as mock_yaml_dump,
            patch("autopkg.log") as _,
        ):

            mock_parser_obj = unittest.mock.Mock()
            mock_parser.return_value = mock_parser_obj

            mock_options = unittest.mock.Mock()
            mock_options.identifier = None
            mock_options.parent_identifier = None
            mock_options.format = "plist"  # Should be overridden by filename

            mock_parse.return_value = (mock_options, ["test.recipe.yaml"])

            autopkg.new_recipe(argv)

            # Verify YAML dump was called
            mock_yaml_dump.assert_called_once()
            args, kwargs = mock_yaml_dump.call_args
            self.assertEqual(kwargs.get("encoding"), "utf-8")

            # Check that MinimumVersion was set to 2.3 for YAML
            recipe = args[0]
            self.assertEqual(recipe["MinimumVersion"], "2.3")

    def test_new_recipe_yaml_format_option(self):
        """Test new_recipe with explicit YAML format option."""
        argv = ["autopkg", "new-recipe", "test.recipe"]

        with (
            patch("autopkg.common_parse") as mock_parse,
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("builtins.open", unittest.mock.mock_open()) as _,
            patch("autopkg.yaml.dump") as mock_yaml_dump,
            patch("autopkg.log") as _,
        ):

            mock_parser_obj = unittest.mock.Mock()
            mock_parser.return_value = mock_parser_obj

            mock_options = unittest.mock.Mock()
            mock_options.identifier = None
            mock_options.parent_identifier = None
            mock_options.format = "yaml"

            mock_parse.return_value = (mock_options, ["test.recipe"])

            autopkg.new_recipe(argv)

            # Verify YAML dump was called
            mock_yaml_dump.assert_called_once()

    def test_new_recipe_no_arguments(self):
        """Test new_recipe with no recipe pathname provided."""
        argv = ["autopkg", "new-recipe"]

        with (
            patch("autopkg.common_parse") as mock_parse,
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("autopkg.log_err") as mock_log_err,
        ):

            mock_parser_obj = unittest.mock.Mock()
            mock_parser.return_value = mock_parser_obj
            mock_parser_obj.get_usage.return_value = "Usage: test"

            mock_options = unittest.mock.Mock()
            mock_parse.return_value = (mock_options, [])  # No arguments

            result = autopkg.new_recipe(argv)

            # Should return -1 and log error
            self.assertEqual(result, -1)
            mock_log_err.assert_any_call("Must specify exactly one recipe pathname!")
            mock_log_err.assert_any_call("Usage: test")

    def test_new_recipe_multiple_arguments(self):
        """Test new_recipe with multiple recipe pathnames provided."""
        argv = ["autopkg", "new-recipe", "recipe1.recipe", "recipe2.recipe"]

        with (
            patch("autopkg.common_parse") as mock_parse,
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("autopkg.log_err") as mock_log_err,
        ):

            mock_parser_obj = unittest.mock.Mock()
            mock_parser.return_value = mock_parser_obj
            mock_parser_obj.get_usage.return_value = "Usage: test"

            mock_options = unittest.mock.Mock()
            mock_parse.return_value = (
                mock_options,
                ["recipe1.recipe", "recipe2.recipe"],
            )

            result = autopkg.new_recipe(argv)

            # Should return -1 and log error
            self.assertEqual(result, -1)
            mock_log_err.assert_any_call("Must specify exactly one recipe pathname!")

    def test_new_recipe_file_write_error(self):
        """Test new_recipe handles file write errors."""
        argv = ["autopkg", "new-recipe", "test.recipe"]

        with (
            patch("autopkg.common_parse") as mock_parse,
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("builtins.open", side_effect=IOError("Permission denied")) as _,
            patch("autopkg.log_err") as mock_log_err,
        ):

            mock_parser_obj = unittest.mock.Mock()
            mock_parser.return_value = mock_parser_obj

            mock_options = unittest.mock.Mock()
            mock_options.identifier = None
            mock_options.parent_identifier = None
            mock_options.format = "plist"

            mock_parse.return_value = (mock_options, ["test.recipe"])

            autopkg.new_recipe(argv)

            # Should log error
            mock_log_err.assert_called_with("Failed to write recipe: Permission denied")

    def test_new_recipe_default_structure(self):
        """Test new_recipe creates recipe with correct default structure."""
        argv = ["autopkg", "new-recipe", "example.recipe"]

        with (
            patch("autopkg.common_parse") as mock_parse,
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("builtins.open", unittest.mock.mock_open()) as _,
            patch("autopkg.plistlib.dump") as _,
            patch("autopkg.log") as _,
            patch("autopkg.plist_serializer") as mock_serializer,
        ):

            mock_parser_obj = unittest.mock.Mock()
            mock_parser.return_value = mock_parser_obj

            mock_options = unittest.mock.Mock()
            mock_options.identifier = None
            mock_options.parent_identifier = None
            mock_options.format = "plist"

            mock_parse.return_value = (mock_options, ["example.recipe"])
            mock_serializer.return_value = {"serialized": "recipe"}

            autopkg.new_recipe(argv)

            # Check the recipe structure
            args, kwargs = mock_serializer.call_args
            recipe = args[0]

            # Verify required fields
            self.assertEqual(recipe["Description"], "Recipe description")
            self.assertEqual(recipe["Identifier"], "local.example")
            self.assertEqual(recipe["Input"]["NAME"], "example")
            self.assertEqual(recipe["MinimumVersion"], "1.0")

            # Verify Process structure
            self.assertEqual(len(recipe["Process"]), 1)
            process_step = recipe["Process"][0]
            self.assertEqual(process_step["Processor"], "ProcessorName")
            self.assertIn("Arguments", process_step)
            self.assertEqual(process_step["Arguments"]["Argument1"], "Value1")
            self.assertEqual(process_step["Arguments"]["Argument2"], "Value2")

    def test_new_recipe_name_extraction(self):
        """Test new_recipe correctly extracts name from different filename formats."""
        test_cases = [
            ("MyApp.recipe", "MyApp", "plist"),
            ("/path/to/SomeApp.recipe", "SomeApp", "plist"),
            ("test.recipe.plist", "test", "plist"),
            ("complex-name.recipe.yaml", "complex-name", "yaml"),
        ]

        for filename, expected_name, expected_format in test_cases:
            with self.subTest(filename=filename):
                argv = ["autopkg", "new-recipe", filename]

                if expected_format == "yaml":
                    with (
                        patch("autopkg.common_parse") as mock_parse,
                        patch("autopkg.gen_common_parser") as mock_parser,
                        patch("builtins.open", unittest.mock.mock_open()),
                        patch("autopkg.yaml.dump") as mock_yaml_dump,
                        patch("autopkg.log"),
                    ):

                        mock_parser_obj = unittest.mock.Mock()
                        mock_parser.return_value = mock_parser_obj

                        mock_options = unittest.mock.Mock()
                        mock_options.identifier = None
                        mock_options.parent_identifier = None
                        mock_options.format = "plist"  # Will be overridden by filename

                        mock_parse.return_value = (mock_options, [filename])

                        autopkg.new_recipe(argv)

                        # Check the name in the recipe from YAML dump
                        args, kwargs = mock_yaml_dump.call_args
                        recipe = args[0]
                        self.assertEqual(recipe["Input"]["NAME"], expected_name)
                        self.assertEqual(recipe["Identifier"], f"local.{expected_name}")
                else:
                    with (
                        patch("autopkg.common_parse") as mock_parse,
                        patch("autopkg.gen_common_parser") as mock_parser,
                        patch("builtins.open", unittest.mock.mock_open()),
                        patch("autopkg.plistlib.dump"),
                        patch("autopkg.log"),
                        patch("autopkg.plist_serializer") as mock_serializer,
                    ):

                        mock_parser_obj = unittest.mock.Mock()
                        mock_parser.return_value = mock_parser_obj

                        mock_options = unittest.mock.Mock()
                        mock_options.identifier = None
                        mock_options.parent_identifier = None
                        mock_options.format = "plist"

                        mock_parse.return_value = (mock_options, [filename])
                        mock_serializer.return_value = {"serialized": "recipe"}

                        autopkg.new_recipe(argv)

                        # Check the name in the recipe
                        args, kwargs = mock_serializer.call_args
                        recipe = args[0]
                        self.assertEqual(recipe["Input"]["NAME"], expected_name)
                        self.assertEqual(recipe["Identifier"], f"local.{expected_name}")


if __name__ == "__main__":
    unittest.main()
