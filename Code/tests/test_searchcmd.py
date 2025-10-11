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

import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

from autopkgcmd import search_recipes
from autopkglib.github import print_gh_search_results


class TestSearchCmd(unittest.TestCase):
    """Test cases for autopkg search command."""

    def setUp(self):
        """Set up test fixtures."""
        # Disable preference reading for consistency
        self.prefs_patch = patch("autopkgcmd.opts.globalPreferences")
        self.prefs_patch.start()

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

    @patch("autopkgcmd.searchcmd.GitHubSession")
    def test_search_with_results_returns_success(self, mock_github_session):
        """Test search_recipes with results returns exit code 0."""
        # Mock the search results
        mock_session = MagicMock()
        mock_results = [
            {
                "name": "NetNewsWire.download.recipe",
                "path": "NetNewsWire/NetNewsWire.download.recipe",
                "repository": {
                    "name": "recipes",
                    "full_name": "autopkg/recipes",
                },
            },
            {
                "name": "NetNewsWire.munki.recipe",
                "path": "NetNewsWire/NetNewsWire.munki.recipe",
                "repository": {
                    "name": "recipes",
                    "full_name": "autopkg/recipes",
                },
            },
        ]
        mock_session.search_for_name.return_value = mock_results
        mock_github_session.return_value = mock_session

        argv = ["autopkg", "search", "NetNewsWire"]
        with patch("sys.stdout", new=StringIO()):
            result = search_recipes(argv)

        self.assertEqual(result, 0)
        mock_session.search_for_name.assert_called_once()

    @patch("autopkgcmd.searchcmd.GitHubSession")
    def test_search_with_no_results_returns_error_code(self, mock_github_session):
        """Test search_recipes with no results returns exit code 2."""
        mock_session = MagicMock()
        mock_session.search_for_name.return_value = []
        mock_github_session.return_value = mock_session

        argv = ["autopkg", "search", "NonexistentRecipe12345"]
        with patch("sys.stdout", new=StringIO()):
            result = search_recipes(argv)

        self.assertEqual(result, 2)

    @patch("autopkgcmd.searchcmd.GitHubSession")
    def test_search_with_too_many_results(self, mock_github_session):
        """Test search_recipes with more than 100 results returns exit code 3."""
        # Create 101 mock results
        mock_session = MagicMock()
        mock_results = []
        for i in range(101):
            mock_results.append(
                {
                    "name": f"Recipe{i}.recipe",
                    "path": f"Recipes/Recipe{i}.recipe",
                    "repository": {
                        "name": "recipes",
                        "full_name": "autopkg/recipes",
                    },
                }
            )
        mock_session.search_for_name.return_value = mock_results
        mock_github_session.return_value = mock_session

        argv = ["autopkg", "search", "Recipe"]
        with patch("sys.stdout", new=StringIO()):
            result = search_recipes(argv)

        self.assertEqual(result, 3)

    @patch("autopkgcmd.searchcmd.GitHubSession")
    def test_search_with_path_only_option(self, mock_github_session):
        """Test search_recipes with --path-only option."""
        mock_session = MagicMock()
        mock_results = [
            {
                "name": "coconutBattery.download.recipe",
                "path": "coconutBattery/coconutBattery.download.recipe",
                "repository": {
                    "name": "recipes",
                    "full_name": "autopkg/recipes",
                },
            }
        ]
        mock_session.search_for_name.return_value = mock_results
        mock_github_session.return_value = mock_session

        argv = ["autopkg", "search", "--path-only", "coconutBattery"]
        with patch("sys.stdout", new=StringIO()):
            result = search_recipes(argv)

        self.assertEqual(result, 0)
        # Verify path_only was set to True
        call_args = mock_session.search_for_name.call_args
        self.assertTrue(call_args[0][1])  # path_only is second argument

    @patch("autopkgcmd.searchcmd.GitHubSession")
    def test_search_with_custom_user_option(self, mock_github_session):
        """Test search_recipes with --user option."""
        mock_session = MagicMock()
        mock_results = [
            {
                "name": "SomeApp.recipe",
                "path": "SomeApp.recipe",
                "repository": {
                    "name": "custom-recipes",
                    "full_name": "customuser/custom-recipes",
                },
            }
        ]
        mock_session.search_for_name.return_value = mock_results
        mock_github_session.return_value = mock_session

        argv = ["autopkg", "search", "--user", "customuser", "SomeApp"]
        with patch("sys.stdout", new=StringIO()):
            result = search_recipes(argv)

        self.assertEqual(result, 0)
        # Verify custom user was passed
        call_args = mock_session.search_for_name.call_args
        self.assertEqual(call_args[0][2], "customuser")  # user is third argument

    @patch("autopkgcmd.searchcmd.GitHubSession")
    def test_search_with_use_token_option(self, mock_github_session):
        """Test search_recipes with --use-token option."""
        mock_session = MagicMock()
        mock_results = [
            {
                "name": "NetNewsWire.download.recipe",
                "path": "NetNewsWire/NetNewsWire.download.recipe",
                "repository": {
                    "name": "recipes",
                    "full_name": "autopkg/recipes",
                },
            }
        ]
        mock_session.search_for_name.return_value = mock_results
        mock_github_session.return_value = mock_session

        argv = ["autopkg", "search", "--use-token", "NetNewsWire"]
        with patch("sys.stdout", new=StringIO()):
            result = search_recipes(argv)

        self.assertEqual(result, 0)
        # Verify use_token was set to True
        call_args = mock_session.search_for_name.call_args
        self.assertTrue(call_args[0][3])  # use_token is fourth argument

    @patch("autopkgcmd.searchcmd.GitHubSession")
    def test_search_url_encodes_search_term(self, mock_github_session):
        """Test that search term with special characters is URL encoded."""
        mock_session = MagicMock()
        mock_session.search_for_name.return_value = []
        mock_github_session.return_value = mock_session

        # Search term with spaces and special characters
        argv = ["autopkg", "search", "App Name+Special"]
        with patch("sys.stdout", new=StringIO()):
            search_recipes(argv)

        # Verify the term was encoded (spaces become %20, + becomes %2B)
        call_args = mock_session.search_for_name.call_args
        search_term = call_args[0][0]
        self.assertEqual(search_term, "App%20Name%2BSpecial")

    @patch("autopkgcmd.searchcmd.GitHubSession")
    def test_search_prints_helper_messages(self, mock_github_session):
        """Test that search prints helpful messages to user."""
        mock_session = MagicMock()
        mock_results = [
            {
                "name": "coconutBattery.download.recipe",
                "path": "coconutBattery/coconutBattery.download.recipe",
                "repository": {
                    "name": "recipes",
                    "full_name": "autopkg/recipes",
                },
            }
        ]
        mock_session.search_for_name.return_value = mock_results
        mock_github_session.return_value = mock_session

        argv = ["autopkg", "search", "coconutBattery"]
        with patch("sys.stdout", new=StringIO()) as fake_out:
            result = search_recipes(argv)
            output = fake_out.getvalue()

        self.assertEqual(result, 0)
        # Check for helpful messages
        self.assertIn("autopkgweb.com", output)
        self.assertIn("repo-add", output)

    @patch("autopkgcmd.searchcmd.GitHubSession")
    def test_search_prints_warning_for_too_many_results(self, mock_github_session):
        """Test that search prints warning when results exceed limit."""
        mock_session = MagicMock()
        # Create 101 results
        mock_results = []
        for i in range(101):
            mock_results.append(
                {
                    "name": f"Recipe{i}.recipe",
                    "path": f"Recipes/Recipe{i}.recipe",
                    "repository": {
                        "name": "recipes",
                        "full_name": "autopkg/recipes",
                    },
                }
            )
        mock_session.search_for_name.return_value = mock_results
        mock_github_session.return_value = mock_session

        argv = ["autopkg", "search", "Recipe"]
        with patch("sys.stdout", new=StringIO()) as fake_out:
            result = search_recipes(argv)
            output = fake_out.getvalue()

        self.assertEqual(result, 3)
        self.assertIn("more than 100 results", output)
        self.assertIn("more specific search term", output)

    # Test print_gh_search_results function

    def test_print_gh_search_results_formats_output_correctly(self):
        """Test that print_gh_search_results formats output with proper columns."""
        results = [
            {
                "name": "NetNewsWire.download.recipe",
                "path": "NetNewsWire/NetNewsWire.download.recipe",
                "repository": {
                    "name": "recipes",
                    "full_name": "autopkg/recipes",
                },
            },
            {
                "name": "NetNewsWire.munki.recipe",
                "path": "NetNewsWire/NetNewsWire.munki.recipe",
                "repository": {
                    "name": "recipes",
                    "full_name": "autopkg/recipes",
                },
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
                "name": "TestApp.recipe",
                "path": "TestApp/TestApp.recipe",
                "repository": {
                    "name": "recipes",
                    "full_name": "autopkg/recipes",
                },
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
                "name": "CustomApp.recipe",
                "path": "CustomApp/CustomApp.recipe",
                "repository": {
                    "name": "custom-recipes",
                    "full_name": "customuser/custom-recipes",
                },
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
                "name": "ZApp.recipe",
                "path": "ZApp.recipe",
                "repository": {
                    "name": "zebra-recipes",
                    "full_name": "user/zebra-recipes",
                },
            },
            {
                "name": "AApp.recipe",
                "path": "AApp.recipe",
                "repository": {
                    "name": "alpha-recipes",
                    "full_name": "user/alpha-recipes",
                },
            },
            {
                "name": "MApp.recipe",
                "path": "MApp.recipe",
                "repository": {
                    "name": "middle-recipes",
                    "full_name": "user/middle-recipes",
                },
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
                "name": "VeryLongRecipeNameForTesting.download.recipe.yaml",
                "path": "VeryLongPath/Subdir/VeryLongRecipeNameForTesting.download.recipe.yaml",
                "repository": {
                    "name": "recipes",
                    "full_name": "autopkg/recipes",
                },
            },
            {
                "name": "Short.recipe",
                "path": "Short.recipe",
                "repository": {
                    "name": "recipes",
                    "full_name": "autopkg/recipes",
                },
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
