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
import tempfile
import unittest
from unittest.mock import Mock, mock_open, patch

# Add the Code directory to the Python path to resolve autopkg dependencies
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

autopkg = imp.load_source(
    "autopkg", os.path.join(os.path.dirname(__file__), "..", "autopkg")
)


class TestAutoPkgOverrides(unittest.TestCase):
    """Test cases for override trust-related functions of AutoPkg."""

    def test_get_trust_info_basic_recipe(self):
        """Test get_trust_info with a basic recipe."""
        mock_recipe = {
            "RECIPE_PATH": "/path/to/test.recipe",
            "PARENT_RECIPES": ["/path/to/parent.recipe"],
            "Process": [
                {"Processor": "URLDownloader"},
                {"Processor": "CustomProcessor"},
            ],
        }

        with patch.object(autopkg, "getsha256hash") as mock_hash, patch.object(
            autopkg, "get_git_commit_hash"
        ) as mock_git_hash, patch.object(
            autopkg, "load_recipe"
        ) as mock_load_recipe, patch.object(
            autopkg, "get_identifier"
        ) as mock_get_identifier, patch.object(
            autopkg, "core_processor_names"
        ) as mock_core_processors, patch.object(
            autopkg, "find_processor_path"
        ) as mock_find_processor, patch.object(
            autopkg, "os_path_compressuser"
        ) as mock_compress:

            mock_hash.side_effect = ["recipe_hash", "parent_hash", "processor_hash"]
            mock_git_hash.side_effect = ["recipe_git", "parent_git", "processor_git"]
            mock_load_recipe.return_value = {"Identifier": "com.test.parent"}
            mock_get_identifier.return_value = "com.test.recipe"
            mock_core_processors.return_value = ["URLDownloader"]
            mock_find_processor.return_value = "/path/to/CustomProcessor.py"
            mock_compress.side_effect = lambda x: x.replace("/Users/test", "~")

            result = autopkg.get_trust_info(mock_recipe)

            self.assertIn("parent_recipes", result)
            self.assertIn("non_core_processors", result)
            self.assertIn("com.test.recipe", result["parent_recipes"])
            self.assertIn("CustomProcessor", result["non_core_processors"])

            # Verify parent recipe info structure
            parent_info = result["parent_recipes"]["com.test.recipe"]
            self.assertIn("path", parent_info)
            self.assertIn("sha256_hash", parent_info)
            self.assertIn("git_hash", parent_info)

            # Verify processor info structure
            processor_info = result["non_core_processors"]["CustomProcessor"]
            self.assertIn("path", processor_info)
            self.assertIn("sha256_hash", processor_info)
            self.assertIn("git_hash", processor_info)

    def test_get_trust_info_processor_not_found(self):
        """Test get_trust_info when a processor path cannot be found."""
        mock_recipe = {
            "RECIPE_PATH": "/path/to/test.recipe",
            "PARENT_RECIPES": [],
            "Process": [{"Processor": "MissingProcessor"}],
        }

        with patch.object(autopkg, "getsha256hash") as mock_hash, patch.object(
            autopkg, "get_git_commit_hash"
        ) as mock_git_hash, patch.object(
            autopkg, "load_recipe"
        ) as mock_load_recipe, patch.object(
            autopkg, "get_identifier"
        ) as mock_get_identifier, patch.object(
            autopkg, "core_processor_names"
        ) as mock_core_processors, patch.object(
            autopkg, "find_processor_path"
        ) as mock_find_processor, patch.object(
            autopkg, "os_path_compressuser"
        ) as mock_compress, patch.object(
            autopkg, "log_err"
        ) as mock_log_err:

            mock_hash.return_value = "recipe_hash"
            mock_git_hash.return_value = "recipe_git"
            mock_load_recipe.return_value = {"Identifier": "com.test.recipe"}
            mock_get_identifier.return_value = "com.test.recipe"
            mock_core_processors.return_value = []
            mock_find_processor.return_value = None  # Processor not found
            mock_compress.side_effect = lambda x: x

            result = autopkg.get_trust_info(mock_recipe)

            # Should still include the processor but with special error values
            processor_info = result["non_core_processors"]["MissingProcessor"]
            self.assertEqual(processor_info["path"], "")
            self.assertEqual(
                processor_info["sha256_hash"], "PROCESSOR FILEPATH NOT FOUND"
            )
            self.assertNotIn("git_hash", processor_info)

            # Should log a warning
            mock_log_err.assert_called_once()

    def test_verify_parent_trust_no_trust_info_override(self):
        """Test verify_parent_trust with no trust info in override recipe."""
        mock_recipe = {
            "RECIPE_PATH": "/overrides/test.recipe",
            "name": "test",
            "PARENT_RECIPES": ["/path/to/parent.recipe"],
        }

        with patch.object(autopkg, "recipe_in_override_dir") as mock_in_override:
            mock_in_override.return_value = True

            with self.assertRaises(autopkg.TrustVerificationWarning) as context:
                autopkg.verify_parent_trust(mock_recipe, ["/overrides"], ["/recipes"])

            self.assertIn("No trust information present", str(context.exception))

    def test_verify_parent_trust_trust_info_in_non_override(self):
        """Test verify_parent_trust with trust info in non-override recipe."""
        mock_recipe = {
            "RECIPE_PATH": "/recipes/test.recipe",
            "ParentRecipeTrustInfo": {"test": "info"},
        }

        with patch.object(autopkg, "recipe_in_override_dir") as mock_in_override:
            mock_in_override.return_value = False

            with self.assertRaises(autopkg.TrustVerificationWarning) as context:
                autopkg.verify_parent_trust(mock_recipe, ["/overrides"], ["/recipes"])

            self.assertIn(
                "Trust information in non-override recipe", str(context.exception)
            )

    def test_verify_parent_trust_external_repo_error(self):
        """Test verify_parent_trust with recipe from external repo."""
        mock_recipe = {
            "RECIPE_PATH": "/external/repo/test.recipe",
            "ParentRecipeTrustInfo": {"test": "info"},
        }

        with patch.object(
            autopkg, "recipe_in_override_dir"
        ) as mock_in_override, patch.object(
            autopkg, "recipe_from_external_repo"
        ) as mock_external, patch.object(
            autopkg, "get_pref"
        ) as mock_get_pref:

            mock_in_override.return_value = True
            mock_external.return_value = True
            mock_get_pref.return_value = "~/Library/AutoPkg/RecipeRepos"

            with self.assertRaises(autopkg.TrustVerificationError) as context:
                autopkg.verify_parent_trust(mock_recipe, ["/overrides"], ["/recipes"])

            self.assertIn("Recipe from external repo", str(context.exception))

    def test_verify_parent_trust_matching_info(self):
        """Test verify_parent_trust with matching trust info."""
        mock_recipe = {
            "RECIPE_PATH": "/overrides/test.recipe",
            "ParentRecipe": "com.test.parent",
            "ParentRecipeTrustInfo": {"test": "info"},
        }

        with patch.object(
            autopkg, "recipe_in_override_dir"
        ) as mock_in_override, patch.object(
            autopkg, "recipe_from_external_repo"
        ) as mock_external, patch.object(
            autopkg, "get_pref"
        ) as mock_get_pref, patch.object(
            autopkg, "load_recipe"
        ) as mock_load_recipe, patch.object(
            autopkg, "get_trust_info"
        ) as mock_get_trust_info:

            mock_in_override.return_value = True
            mock_external.return_value = False
            mock_get_pref.return_value = "~/Library/AutoPkg/RecipeRepos"
            mock_load_recipe.return_value = {"Identifier": "com.test.parent"}
            mock_get_trust_info.return_value = {"test": "info"}  # Matching info

            # Should not raise any exception
            autopkg.verify_parent_trust(mock_recipe, ["/overrides"], ["/recipes"])

    def test_verify_parent_trust_mismatched_processor_hash(self):
        """Test verify_parent_trust with mismatched processor hash."""
        mock_recipe = {
            "RECIPE_PATH": "/overrides/test.recipe",
            "ParentRecipe": "com.test.parent",
            "ParentRecipeTrustInfo": {
                "non_core_processors": {"TestProcessor": {"sha256_hash": "old_hash"}},
                "parent_recipes": {},
            },
        }

        with patch.object(
            autopkg, "recipe_in_override_dir"
        ) as mock_in_override, patch.object(
            autopkg, "recipe_from_external_repo"
        ) as mock_external, patch.object(
            autopkg, "get_pref"
        ) as mock_get_pref, patch.object(
            autopkg, "load_recipe"
        ) as mock_load_recipe, patch.object(
            autopkg, "get_trust_info"
        ) as mock_get_trust_info, patch.object(
            autopkg, "find_processor_path"
        ) as mock_find_processor:

            mock_in_override.return_value = True
            mock_external.return_value = False
            mock_get_pref.return_value = "~/Library/AutoPkg/RecipeRepos"
            mock_load_recipe.return_value = {"Identifier": "com.test.parent"}
            mock_get_trust_info.return_value = {
                "non_core_processors": {"TestProcessor": {"sha256_hash": "new_hash"}},
                "parent_recipes": {},
            }
            mock_find_processor.return_value = "/path/to/TestProcessor.py"

            with self.assertRaises(autopkg.TrustVerificationError) as context:
                autopkg.verify_parent_trust(mock_recipe, ["/overrides"], ["/recipes"])

            self.assertIn("TestProcessor contents differ", str(context.exception))

    @patch("sys.argv", ["autopkg", "update-trust-info", "test.recipe"])
    def test_update_trust_info_success(self):
        """Test update_trust_info command with successful execution."""
        mock_recipe = {"ParentRecipe": "com.test.parent", "Input": {}}
        mock_parent_recipe = {"Identifier": "com.test.parent"}
        mock_trust_info = {"test": "info"}

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
            autopkg, "locate_recipe"
        ) as mock_locate_recipe, patch.object(
            autopkg, "recipe_from_file"
        ) as mock_recipe_from_file, patch.object(
            autopkg, "recipe_in_override_dir"
        ) as mock_in_override, patch.object(
            autopkg, "load_recipe"
        ) as mock_load_recipe, patch.object(
            autopkg, "get_trust_info"
        ) as mock_get_trust_info, patch.object(
            autopkg, "plist_serializer"
        ) as mock_plist_serializer, patch(
            "builtins.open", mock_open()
        ) as _:

            mock_parser = Mock()
            mock_parser_gen.return_value = mock_parser
            mock_options = Mock()
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_parse.return_value = (mock_options, ["test.recipe"])
            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]
            mock_locate_recipe.return_value = "/overrides/test.recipe"
            mock_recipe_from_file.return_value = mock_recipe
            mock_in_override.return_value = True
            mock_load_recipe.return_value = mock_parent_recipe
            mock_get_trust_info.return_value = mock_trust_info
            mock_plist_serializer.return_value = mock_recipe

            result = autopkg.update_trust_info(
                ["autopkg", "update-trust-info", "test.recipe"]
            )

            # Should complete without error
            self.assertIsNone(result)

    @patch("sys.argv", ["autopkg", "update-trust-info"])
    def test_update_trust_info_no_recipes(self):
        """Test update_trust_info command with no recipe names provided."""
        with patch.object(
            autopkg, "gen_common_parser"
        ) as mock_parser_gen, patch.object(
            autopkg, "add_search_and_override_dir_options"
        ), patch.object(
            autopkg, "common_parse"
        ) as mock_parse, patch.object(
            autopkg, "log_err"
        ) as mock_log_err:

            mock_parser = Mock()
            mock_parser_gen.return_value = mock_parser
            mock_options = Mock()
            mock_parse.return_value = (mock_options, [])  # No recipe names

            result = autopkg.update_trust_info(["autopkg", "update-trust-info"])

            self.assertEqual(result, -1)
            mock_log_err.assert_called()

    @patch("sys.argv", ["autopkg", "verify-trust-info", "test.recipe"])
    def test_verify_trust_info_success(self):
        """Test verify_trust_info command with successful verification."""
        mock_recipe = {
            "RECIPE_PATH": "/overrides/test.recipe",
            "ParentRecipe": "com.test.parent",
            "ParentRecipeTrustInfo": {"test": "info"},
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
            autopkg, "verify_parent_trust"
        ) as mock_verify_trust, patch.object(
            autopkg, "log"
        ) as mock_log:

            mock_parser = Mock()
            mock_parser.add_option = Mock()
            mock_parser_gen.return_value = mock_parser
            mock_options = Mock()
            mock_options.recipe_list = None
            mock_options.verbose = 0
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_parse.return_value = (mock_options, ["test.recipe"])
            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]
            mock_load_recipe.return_value = mock_recipe

            result = autopkg.verify_trust_info(
                ["autopkg", "verify-trust-info", "test.recipe"]
            )

            self.assertEqual(result, 0)
            mock_verify_trust.assert_called_once()
            mock_log.assert_called_with("test.recipe: OK")

    @patch("sys.argv", ["autopkg", "verify-trust-info", "test.recipe"])
    def test_verify_trust_info_failure(self):
        """Test verify_trust_info command with verification failure."""
        mock_recipe = {
            "RECIPE_PATH": "/overrides/test.recipe",
            "ParentRecipe": "com.test.parent",
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
            autopkg, "verify_parent_trust"
        ) as mock_verify_trust, patch.object(
            autopkg, "log_err"
        ) as mock_log_err:

            mock_parser = Mock()
            mock_parser.add_option = Mock()
            mock_parser_gen.return_value = mock_parser
            mock_options = Mock()
            mock_options.recipe_list = None
            mock_options.verbose = 0
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_parse.return_value = (mock_options, ["test.recipe"])
            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]
            mock_load_recipe.return_value = mock_recipe
            mock_verify_trust.side_effect = autopkg.TrustVerificationError(
                "Trust failed"
            )

            result = autopkg.verify_trust_info(
                ["autopkg", "verify-trust-info", "test.recipe"]
            )

            self.assertEqual(result, 1)
            mock_log_err.assert_called_with("test.recipe: FAILED")

    def test_trust_verification_warning_exception(self):
        """Test TrustVerificationWarning exception."""
        with self.assertRaises(autopkg.TrustVerificationWarning):
            raise autopkg.TrustVerificationWarning("Test warning")

    def test_trust_verification_error_exception(self):
        """Test TrustVerificationError exception."""
        with self.assertRaises(autopkg.TrustVerificationError):
            raise autopkg.TrustVerificationError("Test error")

    def test_make_override_success_plist_format(self):
        """Test successful override creation in plist format."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.load_recipe"
        ) as mock_load_recipe, patch(
            "autopkg.get_identifier"
        ) as mock_get_identifier, patch(
            "autopkg.get_trust_info"
        ) as mock_get_trust_info, patch(
            "autopkg.remove_recipe_extension"
        ) as mock_remove_recipe_ext, patch(
            "autopkg.log"
        ), patch(
            "os.path.isfile"
        ) as mock_isfile, patch(
            "os.path.exists"
        ) as mock_exists, patch(
            "builtins.open", mock_open()
        ), patch(
            "plistlib.dump"
        ) as mock_plist_dump, patch(
            "autopkg.plist_serializer"
        ) as mock_plist_serializer:

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_options.override_dirs = []
            mock_options.search_dirs = []
            mock_options.name = None
            mock_options.force = False
            mock_options.pull = False
            mock_options.ignore_deprecation = False
            mock_options.format = "plist"
            mock_common_parse.return_value = (mock_options, ["TestApp"])

            with tempfile.TemporaryDirectory() as temp_dir:
                mock_get_override_dirs.return_value = [temp_dir]
                mock_get_search_dirs.return_value = [temp_dir]

                recipe_dict = {
                    "Identifier": "com.example.parent",
                    "Input": {"NAME": "TestApp"},
                    "Process": [{"Processor": "URLDownloader"}],
                    "RECIPE_PATH": "TestApp.recipe",
                }
                mock_load_recipe.return_value = recipe_dict
                mock_get_identifier.return_value = "com.example.parent"
                mock_get_trust_info.return_value = {"test": "trust_info"}
                mock_remove_recipe_ext.return_value = "TestApp"

                # Mock os.path.isfile to return False for recipe names
                mock_isfile.return_value = False

                # Mock os.path.exists to return True for directories, False for files
                def mock_exists_side_effect(path):
                    return path == temp_dir

                mock_exists.side_effect = mock_exists_side_effect
                mock_plist_serializer.return_value = {"test": "serialized"}

                result = autopkg.make_override(["autopkg", "make-override", "TestApp"])

                self.assertEqual(result, 0)
                mock_plist_dump.assert_called_once()

    def test_make_override_success_yaml_format(self):
        """Test successful override creation in yaml format."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.load_recipe"
        ) as mock_load_recipe, patch(
            "autopkg.get_identifier"
        ) as mock_get_identifier, patch(
            "autopkg.get_trust_info"
        ) as mock_get_trust_info, patch(
            "autopkg.remove_recipe_extension"
        ) as mock_remove_recipe_ext, patch(
            "autopkg.log"
        ), patch(
            "os.path.isfile"
        ) as mock_isfile, patch(
            "os.path.exists"
        ) as mock_exists, patch(
            "builtins.open", mock_open()
        ), patch(
            "yaml.dump"
        ) as mock_yaml_dump, patch(
            "autopkg.plist_serializer"
        ) as mock_plist_serializer:

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_options.override_dirs = []
            mock_options.search_dirs = []
            mock_options.name = None
            mock_options.force = False
            mock_options.pull = False
            mock_options.ignore_deprecation = False
            mock_options.format = "yaml"
            mock_common_parse.return_value = (mock_options, ["TestApp"])

            with tempfile.TemporaryDirectory() as temp_dir:
                mock_get_override_dirs.return_value = [temp_dir]
                mock_get_search_dirs.return_value = [temp_dir]

                recipe_dict = {
                    "Identifier": "com.example.parent",
                    "Input": {"NAME": "TestApp"},
                    "Process": [{"Processor": "URLDownloader"}],
                    "RECIPE_PATH": "TestApp.recipe",
                }
                mock_load_recipe.return_value = recipe_dict
                mock_get_identifier.return_value = "com.example.parent"
                mock_get_trust_info.return_value = {"test": "trust_info"}
                mock_remove_recipe_ext.return_value = "TestApp"

                # Mock os.path.isfile to return False for recipe names
                mock_isfile.return_value = False

                # Mock os.path.exists to return True for directories, False for files
                def mock_exists_side_effect(path):
                    return path == temp_dir

                mock_exists.side_effect = mock_exists_side_effect
                mock_plist_serializer.return_value = {"test": "serialized"}

                result = autopkg.make_override(["autopkg", "make-override", "TestApp"])

                self.assertEqual(result, 0)
                mock_yaml_dump.assert_called_once()

    def test_make_override_no_arguments(self):
        """Test make_override with no recipe arguments."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse:

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_common_parse.return_value = (mock_options, [])

            result = autopkg.make_override(["autopkg", "make-override"])

            self.assertEqual(result, -1)

    def test_make_override_multiple_arguments(self):
        """Test make_override with multiple recipe arguments."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse:

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_common_parse.return_value = (mock_options, ["Recipe1", "Recipe2"])

            result = autopkg.make_override(
                ["autopkg", "make-override", "Recipe1", "Recipe2"]
            )

            self.assertEqual(result, -1)

    def test_make_override_absolute_path_error(self):
        """Test make_override with absolute path recipe name."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse, patch("os.path.isfile") as mock_isfile:

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_common_parse.return_value = (mock_options, ["/absolute/path/Recipe"])
            mock_isfile.return_value = True  # Simulate absolute path detection

            result = autopkg.make_override(
                ["autopkg", "make-override", "/absolute/path/Recipe"]
            )

            self.assertEqual(result, -1)

    def test_make_override_recipe_not_found(self):
        """Test make_override when recipe cannot be found."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.load_recipe"
        ) as mock_load_recipe, patch(
            "os.path.isfile"
        ) as mock_isfile, patch(
            "autopkg.log"
        ):

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_options.override_dirs = []
            mock_options.search_dirs = []
            mock_options.pull = False
            mock_common_parse.return_value = (mock_options, ["NonExistentApp"])

            mock_get_override_dirs.return_value = ["/tmp"]
            mock_get_search_dirs.return_value = ["/tmp"]
            mock_isfile.return_value = False
            mock_load_recipe.return_value = None  # Recipe not found

            result = autopkg.make_override(
                ["autopkg", "make-override", "NonExistentApp"]
            )

            self.assertEqual(result, 1)

    def test_make_override_deprecated_recipe_without_ignore(self):
        """Test make_override with deprecated recipe without ignore flag."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.load_recipe"
        ) as mock_load_recipe, patch(
            "autopkg.get_identifier"
        ) as mock_get_identifier, patch(
            "os.path.isfile"
        ) as mock_isfile, patch(
            "autopkg.log"
        ):

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_options.override_dirs = []
            mock_options.search_dirs = []
            mock_options.name = None
            mock_options.force = False
            mock_options.pull = False
            mock_options.ignore_deprecation = False
            mock_options.format = "plist"
            mock_common_parse.return_value = (mock_options, ["DeprecatedApp"])

            mock_get_override_dirs.return_value = ["/tmp"]
            mock_get_search_dirs.return_value = ["/tmp"]
            mock_isfile.return_value = False

            # Recipe with DeprecationWarning processor
            recipe_dict = {
                "Identifier": "com.example.deprecated",
                "Input": {"NAME": "DeprecatedApp"},
                "Process": [
                    {"Processor": "URLDownloader"},
                    {"Processor": "DeprecationWarning"},
                ],
                "RECIPE_PATH": "DeprecatedApp.recipe",
            }
            mock_load_recipe.return_value = recipe_dict
            mock_get_identifier.return_value = "com.example.deprecated"

            result = autopkg.make_override(
                ["autopkg", "make-override", "DeprecatedApp"]
            )

            self.assertEqual(result, 1)

    def test_make_override_no_identifier(self):
        """Test make_override when recipe has no identifier."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.load_recipe"
        ) as mock_load_recipe, patch(
            "autopkg.get_identifier"
        ) as mock_get_identifier, patch(
            "os.path.isfile"
        ) as mock_isfile, patch(
            "autopkg.log"
        ):

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_options.override_dirs = []
            mock_options.search_dirs = []
            mock_options.pull = False
            mock_options.ignore_deprecation = False
            mock_common_parse.return_value = (mock_options, ["NoIdApp"])

            mock_get_override_dirs.return_value = ["/tmp"]
            mock_get_search_dirs.return_value = ["/tmp"]
            mock_isfile.return_value = False

            recipe_dict = {
                "Input": {"NAME": "NoIdApp"},
                "Process": [{"Processor": "URLDownloader"}],
                "RECIPE_PATH": "NoIdApp.recipe",
            }
            mock_load_recipe.return_value = recipe_dict
            mock_get_identifier.return_value = None

            result = autopkg.make_override(["autopkg", "make-override", "NoIdApp"])

            self.assertEqual(result, 1)

    def test_make_override_force_overwrite(self):
        """Test make_override with force overwrite option."""
        with patch("autopkg.gen_common_parser") as mock_parser, patch(
            "autopkg.common_parse"
        ) as mock_common_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.load_recipe"
        ) as mock_load_recipe, patch(
            "autopkg.get_identifier"
        ) as mock_get_identifier, patch(
            "autopkg.get_trust_info"
        ) as mock_get_trust_info, patch(
            "autopkg.remove_recipe_extension"
        ) as mock_remove_recipe_ext, patch(
            "autopkg.log"
        ), patch(
            "os.path.isfile"
        ) as mock_isfile, patch(
            "os.path.exists"
        ) as mock_exists, patch(
            "builtins.open", mock_open()
        ), patch(
            "plistlib.dump"
        ) as mock_plist_dump, patch(
            "autopkg.plist_serializer"
        ) as mock_plist_serializer:

            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance

            mock_options = Mock()
            mock_options.override_dirs = []
            mock_options.search_dirs = []
            mock_options.name = None
            mock_options.force = True
            mock_options.pull = False
            mock_options.ignore_deprecation = False
            mock_options.format = "plist"
            mock_common_parse.return_value = (mock_options, ["TestApp"])

            with tempfile.TemporaryDirectory() as temp_dir:
                mock_get_override_dirs.return_value = [temp_dir]
                mock_get_search_dirs.return_value = [temp_dir]

                recipe_dict = {
                    "Identifier": "com.example.parent",
                    "Input": {"NAME": "TestApp"},
                    "Process": [{"Processor": "URLDownloader"}],
                    "RECIPE_PATH": "TestApp.recipe",
                }
                mock_load_recipe.return_value = recipe_dict
                mock_get_identifier.return_value = "com.example.parent"
                mock_get_trust_info.return_value = {"test": "trust_info"}
                mock_remove_recipe_ext.return_value = "TestApp"

                # Mock os.path.isfile to return False for recipe names, True for existing overrides
                def mock_isfile_side_effect(path):
                    if path == "TestApp":
                        return False  # Recipe name
                    return "TestApp.recipe" in path  # Override file exists

                mock_isfile.side_effect = mock_isfile_side_effect

                # Mock os.path.exists to return True for directories, False for files
                def mock_exists_side_effect(path):
                    return path == temp_dir

                mock_exists.side_effect = mock_exists_side_effect
                mock_plist_serializer.return_value = {"test": "serialized"}

                result = autopkg.make_override(["autopkg", "make-override", "TestApp"])

                self.assertEqual(result, 0)
                mock_plist_dump.assert_called_once()


if __name__ == "__main__":
    unittest.main()
