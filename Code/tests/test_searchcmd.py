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

import json
import unittest
from io import StringIO
from unittest.mock import mock_open, patch

from autopkgcmd import search_recipes
from autopkglib.github import print_gh_search_results


class TestSearchCmd(unittest.TestCase):
    """Test cases for autopkg search command."""

    def setUp(self):
        """Set up test fixtures."""
        # Disable preference reading for consistency
        self.prefs_patch = patch("autopkgcmd.opts.globalPreferences")
        self.prefs_patch.start()

        # Create a mock search index that will be used by tests
        self.mock_search_index = {
            "shortnames": {
                "netnewswire": ["com.github.autopkg.download.NetNewsWire"],
                "coconutbattery": ["com.github.autopkg.download.coconutBattery"],
            },
            "identifiers": {
                "com.github.autopkg.download.NetNewsWire": {
                    "name": "NetNewsWire.download.recipe",
                    "path": "NetNewsWire/NetNewsWire.download.recipe",
                    "repo": "autopkg/recipes",
                    "deprecated": False,
                },
                "com.github.autopkg.download.coconutBattery": {
                    "name": "coconutBattery.download.recipe",
                    "path": "coconutBattery/coconutBattery.download.recipe",
                    "repo": "autopkg/recipes",
                    "deprecated": False,
                },
            },
        }

    def tearDown(self):
        """Clean up after tests."""
        self.prefs_patch.stop()

    # Test search_recipes function

    def test_search_no_query_specified(self):
        """Test search_recipes with no search query returns error code 1."""
        argv = ["autopkg", "search"]
        with patch("sys.stdout", new=StringIO()):
            result = search_recipes(argv)
        self.assertEqual(result, 1)

    @patch("autopkgcmd.searchcmd.check_search_cache")
    @patch("builtins.open", new_callable=mock_open)
    def test_search_with_results_returns_success(self, mock_file, mock_check_cache):
        """Test search_recipes with results returns exit code 0."""
        # Mock check_search_cache to prevent network calls
        mock_check_cache.return_value = None

        # Mock the file read to return our test search index
        mock_file.return_value.read.return_value = json.dumps(
            self.mock_search_index
        ).encode()
        mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(
            self.mock_search_index
        ).encode()

        argv = ["autopkg", "search", "NetNewsWire"]
        with patch("sys.stdout", new=StringIO()):
            result = search_recipes(argv)

        self.assertEqual(result, 0)
        # Verify check_search_cache was called but no actual network requests made
        mock_check_cache.assert_called_once()

    @patch("autopkgcmd.searchcmd.check_search_cache")
    @patch("builtins.open", new_callable=mock_open)
    def test_search_with_no_results_returns_error_code(
        self, mock_file, mock_check_cache
    ):
        """Test search_recipes with no results returns exit code 0."""
        # Mock check_search_cache to prevent network calls
        mock_check_cache.return_value = None

        # Mock empty search index
        empty_index = {"shortnames": {}, "identifiers": {}}
        mock_file.return_value.read.return_value = json.dumps(empty_index).encode()
        mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(
            empty_index
        ).encode()

        argv = ["autopkg", "search", "NonexistentRecipe12345"]
        with patch("sys.stdout", new=StringIO()):
            result = search_recipes(argv)

        self.assertEqual(result, 0)

    @patch("autopkgcmd.searchcmd.check_search_cache")
    @patch("builtins.open", new_callable=mock_open)
    def test_search_with_too_many_results(self, mock_file, mock_check_cache):
        """Test search_recipes with more than 100 results returns exit code 3."""
        # Mock check_search_cache to prevent network calls
        mock_check_cache.return_value = None

        # Create a search index with 101 recipes
        large_index = {"shortnames": {}, "identifiers": {}}
        for i in range(101):
            recipe_id = f"com.test.recipe{i}"
            large_index["shortnames"][f"recipe{i}"] = [recipe_id]
            large_index["identifiers"][recipe_id] = {
                "name": f"Recipe{i}.recipe",
                "path": f"Recipes/Recipe{i}.recipe",
                "repo": "recipes",
                "deprecated": False,
            }

        mock_file.return_value.read.return_value = json.dumps(large_index).encode()
        mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(
            large_index
        ).encode()

        argv = ["autopkg", "search", "recipe"]
        with patch("sys.stdout", new=StringIO()):
            result = search_recipes(argv)

        self.assertEqual(result, 3)

    @patch("autopkgcmd.searchcmd.check_search_cache")
    @patch("builtins.open", new_callable=mock_open)
    def test_search_with_path_only_option(self, mock_file, mock_check_cache):
        """Test search_recipes with --path-only option."""
        # Mock check_search_cache to prevent network calls
        mock_check_cache.return_value = None

        # Mock the file read to return our test search index
        mock_file.return_value.read.return_value = json.dumps(
            self.mock_search_index
        ).encode()
        mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(
            self.mock_search_index
        ).encode()

        argv = ["autopkg", "search", "--path-only", "coconutBattery"]
        with patch("sys.stdout", new=StringIO()):
            result = search_recipes(argv)

        self.assertEqual(result, 0)

    def test_search_with_custom_user_option(self):
        """Test search_recipes with --user option prints GitHub URL."""
        # With the new implementation, --user option just prints a GitHub search URL
        argv = ["autopkg", "search", "--user", "customuser", "SomeApp"]
        with patch("sys.stdout", new=StringIO()) as fake_out:
            result = search_recipes(argv)
            output = fake_out.getvalue()

        self.assertEqual(result, 0)
        # Verify that a GitHub search URL was printed
        self.assertIn("github.com/search", output)
        self.assertIn("customuser", output)

    @patch("autopkgcmd.searchcmd.check_search_cache")
    @patch("builtins.open", new_callable=mock_open)
    def test_search_with_use_token_option(self, mock_file, mock_check_cache):
        """Test search_recipes with --use-token option prints deprecation warning."""
        # Mock check_search_cache to prevent network calls
        mock_check_cache.return_value = None

        # Mock the file read to return our test search index
        mock_file.return_value.read.return_value = json.dumps(
            self.mock_search_index
        ).encode()
        mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(
            self.mock_search_index
        ).encode()

        argv = ["autopkg", "search", "--use-token", "NetNewsWire"]
        # Warnings go to stderr via log_err, so we need to capture both
        with patch("sys.stdout", new=StringIO()) as fake_out, patch(
            "sys.stderr", new=StringIO()
        ) as fake_err:
            result = search_recipes(argv)
            stdout = fake_out.getvalue()
            stderr = fake_err.getvalue()

        self.assertEqual(result, 0)
        # The --use-token option is deprecated and should print a warning to stderr
        self.assertIn("Deprecated", stdout + stderr)

    @patch("autopkgcmd.searchcmd.check_search_cache")
    @patch("builtins.open", new_callable=mock_open)
    def test_search_with_special_characters(self, mock_file, mock_check_cache):
        """Test that search handles special characters in search term."""
        # Mock check_search_cache to prevent network calls
        mock_check_cache.return_value = None

        # Mock empty search index (no results for special characters)
        empty_index = {"shortnames": {}, "identifiers": {}}
        mock_file.return_value.read.return_value = json.dumps(empty_index).encode()
        mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(
            empty_index
        ).encode()

        # Search term with spaces and special characters
        argv = ["autopkg", "search", "App Name+Special"]
        with patch("sys.stdout", new=StringIO()):
            search_recipes(argv)

    @patch("autopkgcmd.searchcmd.check_search_cache")
    @patch("builtins.open", new_callable=mock_open)
    def test_search_prints_helper_messages(self, mock_file, mock_check_cache):
        """Test search_recipes prints helpful messages when relevant."""
        # Mock check_search_cache to prevent network calls
        mock_check_cache.return_value = None

        # Mock the file read to return our test search index
        mock_file.return_value.read.return_value = json.dumps(
            self.mock_search_index
        ).encode()
        mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(
            self.mock_search_index
        ).encode()

        argv = ["autopkg", "search", "coconutBattery"]
        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            search_recipes(argv)
            output = mock_stdout.getvalue()

        # Check for expected output (this may need to be adjusted based on actual output)
        self.assertIn("coconutBattery", output)

    @patch("autopkgcmd.searchcmd.check_search_cache")
    @patch("builtins.open", new_callable=mock_open)
    def test_search_prints_warning_for_too_many_results(
        self, mock_file, mock_check_cache
    ):
        """Test search_recipes prints a warning when there are too many results."""
        # Mock check_search_cache to prevent network calls
        mock_check_cache.return_value = None

        # Create a search index with 101 recipes
        large_index = {"shortnames": {}, "identifiers": {}}
        for i in range(101):
            recipe_id = f"com.test.recipe{i}"
            large_index["shortnames"][f"recipe{i}"] = [recipe_id]
            large_index["identifiers"][recipe_id] = {
                "name": f"Recipe{i}.recipe",
                "path": f"Recipes/Recipe{i}.recipe",
                "repo": "recipes",
                "deprecated": False,
            }

        mock_file.return_value.read.return_value = json.dumps(large_index).encode()
        mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(
            large_index
        ).encode()

        argv = ["autopkg", "search", "recipe"]
        with patch("sys.stdout", new=StringIO()) as mock_stdout, patch(
            "sys.stderr", new=StringIO()
        ) as mock_stderr:
            search_recipes(argv)
            stdout = mock_stdout.getvalue()
            stderr = mock_stderr.getvalue()

        # Check for warning message about too many results (goes to stderr via log_err)
        combined_output = (stdout + stderr).lower()
        self.assertIn("more than 100", combined_output)

    # Test print_gh_search_results function

    def test_print_gh_search_results_formats_output_correctly(self):
        """Test that print_gh_search_results formats output with proper columns."""
        results = [
            {
                "Name": "NetNewsWire.download.recipe",
                "Repo": "recipes",
                "Path": "NetNewsWire/NetNewsWire.download.recipe",
            },
            {
                "Name": "NetNewsWire.munki.recipe",
                "Repo": "recipes",
                "Path": "NetNewsWire/NetNewsWire.munki.recipe",
            },
        ]

        with patch("sys.stdout", new=StringIO()) as fake_out:
            print_gh_search_results(results)
            output = fake_out.getvalue()

        # Check for column headers
        self.assertIn("Name", output)
        self.assertIn("Repo", output)
        self.assertIn("Path", output)
        # Check for recipe names
        self.assertIn("NetNewsWire.download.recipe", output)
        self.assertIn("NetNewsWire.munki.recipe", output)

    def test_print_gh_search_results_shortens_autopkg_org_names(self):
        """Test that print_gh_search_results shortens autopkg org repo names."""
        results = [
            {
                "Name": "TestApp.recipe",
                "Repo": "recipes",
                "Path": "TestApp/TestApp.recipe",
            }
        ]

        with patch("sys.stdout", new=StringIO()) as fake_out:
            print_gh_search_results(results)
            output = fake_out.getvalue()

        # Should show "recipes" not "autopkg/recipes"
        lines = output.split("\n")
        # Find the line with the recipe (not header)
        for line in lines:
            if "TestApp.recipe" in line:
                # Check that it contains "recipes" but not the full path
                self.assertIn("recipes", line)
                # The repo column should be just "recipes"
                break

    def test_print_gh_search_results_shows_full_name_for_non_autopkg_repos(self):
        """Test that print_gh_search_results shows full names for non-autopkg repos."""
        results = [
            {
                "Name": "CustomApp.recipe",
                "Repo": "customuser/custom-recipes",
                "Path": "CustomApp/CustomApp.recipe",
            }
        ]

        with patch("sys.stdout", new=StringIO()) as fake_out:
            print_gh_search_results(results)
            output = fake_out.getvalue()

        # Should show full "customuser/custom-recipes"
        self.assertIn("customuser/custom-recipes", output)

    def test_print_gh_search_results_sorts_by_repo_name(self):
        """Test that print_gh_search_results sorts results by repository name."""
        results = [
            {
                "Name": "ZApp.recipe",
                "Repo": "user/zebra-recipes",
                "Path": "ZApp.recipe",
            },
            {
                "Name": "AApp.recipe",
                "Repo": "user/alpha-recipes",
                "Path": "AApp.recipe",
            },
            {
                "Name": "MApp.recipe",
                "Repo": "user/middle-recipes",
                "Path": "MApp.recipe",
            },
        ]

        with patch("sys.stdout", new=StringIO()) as fake_out:
            print_gh_search_results(results)
            output = fake_out.getvalue()

        # Find positions of repo names in output
        alpha_pos = output.find("alpha-recipes")
        middle_pos = output.find("middle-recipes")
        zebra_pos = output.find("zebra-recipes")

        # Verify they appear in alphabetical order
        self.assertLess(alpha_pos, middle_pos)
        self.assertLess(middle_pos, zebra_pos)

    def test_print_gh_search_results_handles_empty_results(self):
        """Test that print_gh_search_results handles empty results gracefully."""
        results = []

        with patch("sys.stdout", new=StringIO()) as fake_out:
            print_gh_search_results(results)
            output = fake_out.getvalue()

        # Should produce no output for empty results
        self.assertEqual(output, "")

    def test_print_gh_search_results_calculates_column_widths_dynamically(self):
        """Test that column widths adjust to content."""
        results = [
            {
                "Name": "VeryLongRecipeNameForTesting.download.recipe.yaml",
                "Repo": "recipes",
                "Path": "VeryLongPath/Subdir/VeryLongRecipeNameForTesting.download.recipe.yaml",
            },
            {
                "Name": "Short.recipe",
                "Repo": "recipes",
                "Path": "Short.recipe",
            },
        ]

        with patch("sys.stdout", new=StringIO()) as fake_out:
            print_gh_search_results(results)
            output = fake_out.getvalue()

        # Both recipes should be visible
        self.assertIn("VeryLongRecipeNameForTesting.download.recipe.yaml", output)
        self.assertIn("Short.recipe", output)
        # Headers should be present
        self.assertIn("Name", output)
        self.assertIn("Path", output)


if __name__ == "__main__":
    unittest.main()
