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
from unittest.mock import Mock, mock_open, patch

# Add the Code directory to the Python path to resolve autopkg dependencies
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

autopkg = imp.load_source(
    "autopkg", os.path.join(os.path.dirname(__file__), "..", "autopkg")
)


class TestAutoPkgTrust(unittest.TestCase):
    """Test cases for override trust-related functions of AutoPkg."""

    def setUp(self):
        if autopkg is None:
            self.skipTest("autopkg module could not be imported")

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
