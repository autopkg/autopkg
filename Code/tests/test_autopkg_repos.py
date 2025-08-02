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
from unittest.mock import Mock, patch

# Add the Code directory to the Python path to resolve autopkg dependencies
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

autopkg = imp.load_source(
    "autopkg", os.path.join(os.path.dirname(__file__), "..", "autopkg")
)


class TestAutoPkgRepos(unittest.TestCase):
    """Test cases for repository-related functions of AutoPkg."""

    def test_expand_single_autopkg_org_urls(self):
        """Expand single part short repo URLs in the AutoPkg org on GitHub"""
        url = autopkg.expand_repo_url("recipes")
        self.assertEqual(url, "https://github.com/autopkg/recipes")
        url = autopkg.expand_repo_url("bogus")
        self.assertEqual(url, "https://github.com/autopkg/bogus")

    def test_expand_multi_autopkg_org_urls(self):
        """Expand multi part short repo URLs in the AutoPkg org on GitHub"""
        url = autopkg.expand_repo_url("autopkg/recipes")
        self.assertEqual(url, "https://github.com/autopkg/recipes")
        url = autopkg.expand_repo_url("autopkg/bogus")
        self.assertEqual(url, "https://github.com/autopkg/bogus")

    def test_expand_multi_other_org_urls(self):
        """Expand multi part short repo URLs in another org on GitHub"""
        url = autopkg.expand_repo_url("eth-its/autopkg-mac-recipes")
        self.assertEqual(url, "https://github.com/eth-its/autopkg-mac-recipes")
        url = autopkg.expand_repo_url("facebook/Recipes-For-AutoPkg")
        self.assertEqual(url, "https://github.com/facebook/Recipes-For-AutoPkg")
        url = autopkg.expand_repo_url("bogusorg/bogusrepo")
        self.assertEqual(url, "https://github.com/bogusorg/bogusrepo")

    def test_expand_full_urls(self):
        """Expand full URLs"""
        url = autopkg.expand_repo_url("http://github.com/eth-its/autopkg-mac-recipes")
        self.assertEqual(url, "http://github.com/eth-its/autopkg-mac-recipes")
        url = autopkg.expand_repo_url("https://github.com/eth-its/autopkg-mac-recipes")
        self.assertEqual(url, "https://github.com/eth-its/autopkg-mac-recipes")
        url = autopkg.expand_repo_url("http://github.com/facebook/Recipes-For-AutoPkg")
        self.assertEqual(url, "http://github.com/facebook/Recipes-For-AutoPkg")
        url = autopkg.expand_repo_url("https://github.com/facebook/Recipes-For-AutoPkg")
        self.assertEqual(url, "https://github.com/facebook/Recipes-For-AutoPkg")
        url = autopkg.expand_repo_url("http://github.com/bogusorg/bogusrepo")
        self.assertEqual(url, "http://github.com/bogusorg/bogusrepo")
        url = autopkg.expand_repo_url("https://github.com/bogusorg/bogusrepo")
        self.assertEqual(url, "https://github.com/bogusorg/bogusrepo")

    # TODO: Not yet implemented.
    # def test_expand_file_urls(self):
    #     """Expand file URLs"""
    #     url = autopkg.expand_repo_url("file:///private/tmp/")
    #     self.assertEqual(url, "/private/tmp/")
    #     url = autopkg.expand_repo_url("file:///foo/bar/")
    #     self.assertEqual(url, "/foo/bar/")

    def test_expand_file_paths(self):
        """Expand file paths"""
        url = autopkg.expand_repo_url("/private/tmp/")
        self.assertEqual(url, "/private/tmp")
        url = autopkg.expand_repo_url("/foo/bar/")
        self.assertEqual(url, "/foo/bar")
        url = autopkg.expand_repo_url("/foo/bar")
        self.assertEqual(url, "/foo/bar")
        url = autopkg.expand_repo_url(
            "~/Library/AutoPkg/RecipeRepos/com.github.autopkg.recipes"
        )
        self.assertEqual(
            url, "~/Library/AutoPkg/RecipeRepos/com.github.autopkg.recipes"
        )
        url = autopkg.expand_repo_url("/Users/Shared/foo")
        self.assertEqual(url, "/Users/Shared/foo")

    # Tests for get_repository_from_identifier function
    @patch("autopkg.do_gh_repo_contents_fetch")
    @patch("autopkg.GitHubSession")
    def test_get_repository_from_identifier_valid_identifier(
        self, mock_github_session, mock_fetch
    ):
        """Test get_repository_from_identifier with valid identifier."""
        # Mock GitHubSession and search results
        mock_session = Mock()
        mock_github_session.return_value = mock_session
        mock_session.search_for_name.return_value = [
            {
                "repository": {"name": "recipes"},
                "path": "TestApp/TestApp.recipe",
            }
        ]

        # Mock file contents fetch
        recipe_plist = {
            "Identifier": "com.test.recipe",
            "Description": "Test recipe",
            "Input": {"NAME": "TestApp"},
            "Process": [],
        }
        mock_fetch.return_value = plistlib.dumps(recipe_plist)

        # Mock plistlib.loads
        with patch("autopkg.plistlib.loads") as mock_loads:
            mock_loads.return_value = recipe_plist

            result = autopkg.get_repository_from_identifier("com.test.recipe")

            self.assertEqual(result, "recipes")
            mock_session.search_for_name.assert_called_once_with("com.test.recipe")
            mock_fetch.assert_called_once_with("recipes", "TestApp/TestApp.recipe")

    @patch("autopkg.do_gh_repo_contents_fetch")
    @patch("autopkg.GitHubSession")
    def test_get_repository_from_identifier_no_match(
        self, mock_github_session, mock_fetch
    ):
        """Test get_repository_from_identifier with no matching identifier."""
        # Mock GitHubSession and search results
        mock_session = Mock()
        mock_github_session.return_value = mock_session
        mock_session.search_for_name.return_value = [
            {
                "repository": {"name": "recipes"},
                "path": "TestApp/TestApp.recipe",
            }
        ]

        # Mock file contents fetch with different identifier
        recipe_plist = {
            "Identifier": "com.different.recipe",
            "Description": "Different recipe",
            "Input": {"NAME": "TestApp"},
            "Process": [],
        }
        mock_fetch.return_value = plistlib.dumps(recipe_plist)

        # Mock plistlib.loads
        with patch("autopkg.plistlib.loads") as mock_loads:
            mock_loads.return_value = recipe_plist

            result = autopkg.get_repository_from_identifier("com.test.recipe")

            self.assertIsNone(result)
            mock_session.search_for_name.assert_called_once_with("com.test.recipe")

    @patch("autopkg.GitHubSession")
    def test_get_repository_from_identifier_invalid_identifier(
        self, mock_github_session
    ):
        """Test get_repository_from_identifier with invalid identifier format."""
        # Mock GitHubSession and search results
        mock_session = Mock()
        mock_github_session.return_value = mock_session
        mock_session.search_for_name.return_value = []

        # Test with identifier that doesn't start with 'com'
        result = autopkg.get_repository_from_identifier("invalid.identifier")
        self.assertIsNone(result)

        # GitHubSession is called first, but then the identifier check happens
        mock_github_session.assert_called_once()
        mock_session.search_for_name.assert_called_once_with("invalid.identifier")

    @patch("autopkg.GitHubSession")
    def test_get_repository_from_identifier_non_identifier_format(
        self, mock_github_session
    ):
        """Test get_repository_from_identifier with non-identifier format."""
        # Mock GitHubSession and search results
        mock_session = Mock()
        mock_github_session.return_value = mock_session
        mock_session.search_for_name.return_value = []

        # Test with simple name that's not an identifier
        result = autopkg.get_repository_from_identifier("TestApp")
        self.assertIsNone(result)

        # GitHubSession is called first, but then the identifier check happens
        mock_github_session.assert_called_once()
        mock_session.search_for_name.assert_called_once_with("TestApp")

    @patch("autopkg.do_gh_repo_contents_fetch")
    @patch("autopkg.GitHubSession")
    def test_get_repository_from_identifier_multiple_repos_first_match(
        self, mock_github_session, mock_fetch
    ):
        """Test get_repository_from_identifier with multiple repos, first match wins."""
        # Mock GitHubSession and search results with multiple repos
        mock_session = Mock()
        mock_github_session.return_value = mock_session
        mock_session.search_for_name.return_value = [
            {
                "repository": {"name": "recipes"},
                "path": "TestApp/TestApp.recipe",
            },
            {
                "repository": {"name": "other-recipes"},
                "path": "TestApp/TestApp.recipe",
            },
        ]

        # Mock file contents fetch - first repo has matching identifier
        matching_plist = {
            "Identifier": "com.test.recipe",
            "Description": "Test recipe",
            "Input": {"NAME": "TestApp"},
            "Process": [],
        }

        def mock_fetch_side_effect(repo_name, _path):
            if repo_name == "recipes":
                return plistlib.dumps(matching_plist)
            else:
                # Other repos don't match
                return plistlib.dumps(
                    {
                        "Identifier": "com.other.recipe",
                        "Description": "Other recipe",
                    }
                )

        mock_fetch.side_effect = mock_fetch_side_effect

        # Mock plistlib.loads
        with patch("autopkg.plistlib.loads") as mock_loads:
            mock_loads.side_effect = [matching_plist]

            result = autopkg.get_repository_from_identifier("com.test.recipe")

            self.assertEqual(result, "recipes")
            mock_session.search_for_name.assert_called_once_with("com.test.recipe")
            # Should only fetch from first repo since it matched
            mock_fetch.assert_called_once_with("recipes", "TestApp/TestApp.recipe")

    @patch("autopkg.do_gh_repo_contents_fetch")
    @patch("autopkg.GitHubSession")
    def test_get_repository_from_identifier_empty_search_results(
        self, mock_github_session, mock_fetch
    ):
        """Test get_repository_from_identifier with empty search results."""
        # Mock GitHubSession with empty search results
        mock_session = Mock()
        mock_github_session.return_value = mock_session
        mock_session.search_for_name.return_value = []

        result = autopkg.get_repository_from_identifier("com.test.recipe")

        self.assertIsNone(result)
        mock_session.search_for_name.assert_called_once_with("com.test.recipe")
        mock_fetch.assert_not_called()

    @patch("autopkg.do_gh_repo_contents_fetch")
    @patch("autopkg.GitHubSession")
    def test_get_repository_from_identifier_plistlib_error(
        self, mock_github_session, mock_fetch
    ):
        """Test get_repository_from_identifier when plistlib fails to parse."""
        # Mock GitHubSession and search results
        mock_session = Mock()
        mock_github_session.return_value = mock_session
        mock_session.search_for_name.return_value = [
            {
                "repository": {"name": "recipes"},
                "path": "TestApp/TestApp.recipe",
            }
        ]

        # Mock file contents fetch returns invalid plist data
        mock_fetch.return_value = b"invalid plist data"

        # Mock plistlib.loads to raise an exception
        with patch("autopkg.plistlib.loads") as mock_loads:
            mock_loads.side_effect = plistlib.InvalidFileException("Invalid plist")

            # The function doesn't handle the exception, so it should propagate
            with self.assertRaises(plistlib.InvalidFileException):
                autopkg.get_repository_from_identifier("com.test.recipe")

            mock_session.search_for_name.assert_called_once_with("com.test.recipe")
            mock_fetch.assert_called_once_with("recipes", "TestApp/TestApp.recipe")

    @patch("autopkg.do_gh_repo_contents_fetch")
    @patch("autopkg.GitHubSession")
    def test_get_repository_from_identifier_with_print_output(
        self, mock_github_session, mock_fetch
    ):
        """Test get_repository_from_identifier prints found repository."""
        # Mock GitHubSession and search results
        mock_session = Mock()
        mock_github_session.return_value = mock_session
        mock_session.search_for_name.return_value = [
            {
                "repository": {"name": "test-recipes"},
                "path": "TestApp/TestApp.recipe",
            }
        ]

        # Mock file contents fetch
        recipe_plist = {
            "Identifier": "com.test.recipe",
            "Description": "Test recipe",
            "Input": {"NAME": "TestApp"},
            "Process": [],
        }
        mock_fetch.return_value = plistlib.dumps(recipe_plist)

        # Mock plistlib.loads and print
        with patch("autopkg.plistlib.loads") as mock_loads, patch(
            "builtins.print"
        ) as mock_print:
            mock_loads.return_value = recipe_plist

            result = autopkg.get_repository_from_identifier("com.test.recipe")

            self.assertEqual(result, "test-recipes")
            mock_print.assert_called_once_with(
                "Found this recipe in repository: test-recipes"
            )

    # Tests for get_recipe_repo function
    @patch("autopkg.run_git")
    @patch("autopkg.git_cmd")
    @patch("autopkg.get_pref")
    @patch("os.path.exists")
    @patch("os.path.expanduser")
    @patch("os.path.abspath")
    def test_get_recipe_repo_clone_new_repo(
        self,
        mock_abspath,
        mock_expanduser,
        mock_exists,
        mock_get_pref,
        mock_git_cmd,
        mock_run_git,
    ):
        """Test get_recipe_repo cloning a new repository."""
        # Setup mocks
        mock_get_pref.return_value = "~/Library/AutoPkg/RecipeRepos"
        mock_expanduser.return_value = "/Users/test/Library/AutoPkg/RecipeRepos"
        mock_abspath.return_value = (
            "/Users/test/Library/AutoPkg/RecipeRepos/com.github.autopkg.recipes"
        )
        mock_exists.return_value = False  # Directory doesn't exist
        mock_git_cmd.return_value = "/usr/bin/git"
        mock_run_git.return_value = "Cloning into 'recipes'..."

        with patch("autopkg.log") as mock_log:
            result = autopkg.get_recipe_repo("https://github.com/autopkg/recipes")

            self.assertEqual(
                result,
                "/Users/test/Library/AutoPkg/RecipeRepos/com.github.autopkg.recipes",
            )
            mock_git_cmd.assert_called_once()
            mock_run_git.assert_called_once_with(
                [
                    "clone",
                    "https://github.com/autopkg/recipes",
                    "/Users/test/Library/AutoPkg/RecipeRepos/com.github.autopkg.recipes",
                ]
            )
            mock_log.assert_called()

    @patch("autopkg.run_git")
    @patch("autopkg.git_cmd")
    @patch("autopkg.get_pref")
    @patch("os.path.exists")
    @patch("os.path.expanduser")
    @patch("os.path.abspath")
    @patch("os.path.isdir")
    def test_get_recipe_repo_pull_existing_repo(
        self,
        mock_isdir,
        mock_abspath,
        mock_expanduser,
        mock_exists,
        mock_get_pref,
        mock_git_cmd,
        mock_run_git,
    ):
        """Test get_recipe_repo pulling an existing repository."""
        # Setup mocks
        mock_get_pref.return_value = "~/Library/AutoPkg/RecipeRepos"
        mock_expanduser.return_value = "/Users/test/Library/AutoPkg/RecipeRepos"
        mock_abspath.return_value = (
            "/Users/test/Library/AutoPkg/RecipeRepos/com.github.autopkg.recipes"
        )
        mock_exists.return_value = True  # Directory exists
        mock_isdir.return_value = True  # .git directory exists
        mock_git_cmd.return_value = "/usr/bin/git"
        mock_run_git.return_value = "Already up to date."

        with patch("autopkg.log") as mock_log:
            result = autopkg.get_recipe_repo("https://github.com/autopkg/recipes")

            self.assertEqual(
                result,
                "/Users/test/Library/AutoPkg/RecipeRepos/com.github.autopkg.recipes",
            )
            mock_git_cmd.assert_called_once()
            mock_run_git.assert_called_once_with(
                ["pull"],
                git_directory="/Users/test/Library/AutoPkg/RecipeRepos/com.github.autopkg.recipes",
            )
            mock_log.assert_called()

    @patch("autopkg.git_cmd")
    @patch("autopkg.log_err")
    def test_get_recipe_repo_no_git_command(self, mock_log_err, mock_git_cmd):
        """Test get_recipe_repo when git command is not available."""
        mock_git_cmd.return_value = None

        result = autopkg.get_recipe_repo("https://github.com/autopkg/recipes")

        self.assertIsNone(result)
        mock_log_err.assert_called_once_with("No git binary could be found!")

    @patch("autopkg.run_git")
    @patch("autopkg.git_cmd")
    @patch("autopkg.get_pref")
    @patch("os.path.exists")
    @patch("os.path.expanduser")
    @patch("os.path.abspath")
    @patch("os.path.isdir")
    @patch("autopkg.log_err")
    def test_get_recipe_repo_existing_non_git_directory(
        self,
        mock_log_err,
        mock_isdir,
        mock_abspath,
        mock_expanduser,
        mock_exists,
        mock_get_pref,
        mock_git_cmd,
        mock_run_git,
    ):
        """Test get_recipe_repo when directory exists but is not a git repo."""
        # Setup mocks
        mock_get_pref.return_value = "~/Library/AutoPkg/RecipeRepos"
        mock_expanduser.return_value = "/Users/test/Library/AutoPkg/RecipeRepos"
        mock_abspath.return_value = (
            "/Users/test/Library/AutoPkg/RecipeRepos/com.github.autopkg.recipes"
        )
        mock_exists.return_value = True  # Directory exists
        mock_isdir.return_value = False  # .git directory doesn't exist
        mock_git_cmd.return_value = "/usr/bin/git"

        result = autopkg.get_recipe_repo("https://github.com/autopkg/recipes")

        self.assertIsNone(result)
        mock_log_err.assert_called_once_with(
            "/Users/test/Library/AutoPkg/RecipeRepos/com.github.autopkg.recipes exists and is not a git repo!"
        )
        mock_run_git.assert_not_called()

    @patch("autopkg.run_git")
    @patch("autopkg.git_cmd")
    @patch("autopkg.get_pref")
    @patch("os.path.exists")
    @patch("os.path.expanduser")
    @patch("os.path.abspath")
    @patch("autopkg.log_err")
    def test_get_recipe_repo_clone_error(
        self,
        mock_log_err,
        mock_abspath,
        mock_expanduser,
        mock_exists,
        mock_get_pref,
        mock_git_cmd,
        mock_run_git,
    ):
        """Test get_recipe_repo when git clone fails."""
        # Setup mocks
        mock_get_pref.return_value = "~/Library/AutoPkg/RecipeRepos"
        mock_expanduser.return_value = "/Users/test/Library/AutoPkg/RecipeRepos"
        mock_abspath.return_value = (
            "/Users/test/Library/AutoPkg/RecipeRepos/com.github.autopkg.recipes"
        )
        mock_exists.return_value = False  # Directory doesn't exist
        mock_git_cmd.return_value = "/usr/bin/git"
        mock_run_git.side_effect = autopkg.GitError("fatal: repository not found")

        with patch("autopkg.log") as mock_log:
            result = autopkg.get_recipe_repo("https://github.com/invalid/repo")

            self.assertIsNone(result)
            mock_log_err.assert_called_once()
            mock_log.assert_called()

    @patch("autopkg.run_git")
    @patch("autopkg.git_cmd")
    @patch("autopkg.get_pref")
    @patch("os.path.exists")
    @patch("os.path.expanduser")
    @patch("os.path.abspath")
    @patch("os.path.isdir")
    @patch("autopkg.log_err")
    def test_get_recipe_repo_pull_error(
        self,
        mock_log_err,
        mock_isdir,
        mock_abspath,
        mock_expanduser,
        mock_exists,
        mock_get_pref,
        mock_git_cmd,
        mock_run_git,
    ):
        """Test get_recipe_repo when git pull fails."""
        # Setup mocks
        mock_get_pref.return_value = "~/Library/AutoPkg/RecipeRepos"
        mock_expanduser.return_value = "/Users/test/Library/AutoPkg/RecipeRepos"
        mock_abspath.return_value = (
            "/Users/test/Library/AutoPkg/RecipeRepos/com.github.autopkg.recipes"
        )
        mock_exists.return_value = True  # Directory exists
        mock_isdir.return_value = True  # .git directory exists
        mock_git_cmd.return_value = "/usr/bin/git"
        mock_run_git.side_effect = autopkg.GitError("fatal: unable to access")

        with patch("autopkg.log") as mock_log:
            result = autopkg.get_recipe_repo("https://github.com/autopkg/recipes")

            self.assertIsNone(result)
            mock_log_err.assert_called_once()
            mock_log.assert_called()

    @patch("autopkg.run_git")
    @patch("autopkg.git_cmd")
    @patch("autopkg.get_pref")
    @patch("os.path.exists")
    @patch("os.path.expanduser")
    @patch("os.path.abspath")
    def test_get_recipe_repo_url_parsing(
        self,
        mock_abspath,
        mock_expanduser,
        mock_exists,
        mock_get_pref,
        mock_git_cmd,
        mock_run_git,
    ):
        """Test get_recipe_repo URL parsing for different URL formats."""
        # Setup mocks
        mock_get_pref.return_value = "~/Library/AutoPkg/RecipeRepos"
        mock_expanduser.return_value = "/Users/test/Library/AutoPkg/RecipeRepos"
        mock_exists.return_value = False
        mock_git_cmd.return_value = "/usr/bin/git"
        mock_run_git.return_value = "Cloning..."

        # Test different URL formats and their expected directory names
        test_cases = [
            (
                "https://github.com/autopkg/recipes",
                "/Users/test/Library/AutoPkg/RecipeRepos/com.github.autopkg.recipes",
            ),
            (
                "https://github.com/user/repo.git",
                "/Users/test/Library/AutoPkg/RecipeRepos/com.github.user.repo",
            ),
            (
                "ssh://git@github.com/user/repo",
                "/Users/test/Library/AutoPkg/RecipeRepos/com.github.user.repo",
            ),
        ]

        for git_url, expected_path in test_cases:
            with self.subTest(git_url=git_url):
                mock_abspath.return_value = expected_path
                mock_run_git.reset_mock()

                with patch("autopkg.log"):
                    result = autopkg.get_recipe_repo(git_url)

                self.assertEqual(result, expected_path)
                mock_run_git.assert_called_once_with(["clone", git_url, expected_path])

    @patch("autopkg.run_git")
    @patch("autopkg.git_cmd")
    @patch("autopkg.get_pref")
    @patch("os.path.exists")
    @patch("os.path.expanduser")
    @patch("os.path.abspath")
    def test_get_recipe_repo_custom_repo_dir(
        self,
        mock_abspath,
        mock_expanduser,
        mock_exists,
        mock_get_pref,
        mock_git_cmd,
        mock_run_git,
    ):
        """Test get_recipe_repo with custom RECIPE_REPO_DIR preference."""
        # Setup mocks with custom repo directory
        mock_get_pref.return_value = "/custom/repo/dir"
        mock_expanduser.return_value = "/custom/repo/dir"
        mock_abspath.return_value = "/custom/repo/dir/com.github.autopkg.recipes"
        mock_exists.return_value = False
        mock_git_cmd.return_value = "/usr/bin/git"
        mock_run_git.return_value = "Cloning..."

        with patch("autopkg.log"):
            result = autopkg.get_recipe_repo("https://github.com/autopkg/recipes")

            self.assertEqual(result, "/custom/repo/dir/com.github.autopkg.recipes")
            mock_get_pref.assert_called_once_with("RECIPE_REPO_DIR")
            mock_expanduser.assert_called_once_with("/custom/repo/dir")

    @patch("autopkg.run_git")
    @patch("autopkg.git_cmd")
    @patch("autopkg.get_pref")
    @patch("os.path.exists")
    @patch("os.path.expanduser")
    @patch("os.path.abspath")
    def test_get_recipe_repo_user_in_url(
        self,
        mock_abspath,
        mock_expanduser,
        mock_exists,
        mock_get_pref,
        mock_git_cmd,
        mock_run_git,
    ):
        """Test get_recipe_repo strips user from URL when parsing domain."""
        # Setup mocks
        mock_get_pref.return_value = "~/Library/AutoPkg/RecipeRepos"
        mock_expanduser.return_value = "/Users/test/Library/AutoPkg/RecipeRepos"
        mock_abspath.return_value = (
            "/Users/test/Library/AutoPkg/RecipeRepos/com.github.user.repo"
        )
        mock_exists.return_value = False
        mock_git_cmd.return_value = "/usr/bin/git"
        mock_run_git.return_value = "Cloning..."

        with patch("autopkg.log"):
            result = autopkg.get_recipe_repo("https://username@github.com/user/repo")

            # Should still parse domain correctly despite username in URL
            self.assertEqual(
                result, "/Users/test/Library/AutoPkg/RecipeRepos/com.github.user.repo"
            )

    # Tests for get_repo_info function
    @patch("autopkg.get_pref")
    def test_get_repo_info_url_found(self, mock_get_pref):
        """Test get_repo_info with URL that matches a known repo."""
        mock_recipe_repos = {
            "/Users/test/Repos/recipes": {
                "URL": "https://github.com/autopkg/recipes",
                "branch": "main",
            },
            "/Users/test/Repos/other": {
                "URL": "https://github.com/user/other-recipes",
                "branch": "dev",
            },
        }
        mock_get_pref.return_value = mock_recipe_repos

        result = autopkg.get_repo_info("https://github.com/autopkg/recipes")

        expected = {
            "path": "/Users/test/Repos/recipes",
            "URL": "https://github.com/autopkg/recipes",
            "branch": "main",
        }
        self.assertEqual(result, expected)

    @patch("autopkg.get_pref")
    def test_get_repo_info_url_not_found(self, mock_get_pref):
        """Test get_repo_info with URL that doesn't match any known repo."""
        mock_recipe_repos = {
            "/Users/test/Repos/recipes": {
                "URL": "https://github.com/autopkg/recipes",
            }
        }
        mock_get_pref.return_value = mock_recipe_repos

        result = autopkg.get_repo_info("https://github.com/nonexistent/repo")

        self.assertEqual(result, {})

    @patch("autopkg.get_pref")
    @patch("os.path.abspath")
    @patch("os.path.expanduser")
    def test_get_repo_info_path_found(
        self, mock_expanduser, mock_abspath, mock_get_pref
    ):
        """Test get_repo_info with local path that matches a known repo."""
        mock_expanduser.return_value = "/Users/test/Repos/recipes"
        mock_abspath.return_value = "/Users/test/Repos/recipes"
        mock_recipe_repos = {
            "/Users/test/Repos/recipes": {
                "URL": "https://github.com/autopkg/recipes",
                "branch": "main",
            }
        }
        mock_get_pref.return_value = mock_recipe_repos

        result = autopkg.get_repo_info("~/Repos/recipes")

        expected = {
            "path": "/Users/test/Repos/recipes",
            "URL": "https://github.com/autopkg/recipes",
            "branch": "main",
        }
        self.assertEqual(result, expected)
        mock_expanduser.assert_called_once_with("~/Repos/recipes")
        mock_abspath.assert_called_once_with("/Users/test/Repos/recipes")

    @patch("autopkg.get_pref")
    @patch("os.path.abspath")
    @patch("os.path.expanduser")
    def test_get_repo_info_path_not_found(
        self, mock_expanduser, mock_abspath, mock_get_pref
    ):
        """Test get_repo_info with local path that doesn't match any known repo."""
        mock_expanduser.return_value = "/Users/test/Repos/unknown"
        mock_abspath.return_value = "/Users/test/Repos/unknown"
        mock_recipe_repos = {
            "/Users/test/Repos/recipes": {
                "URL": "https://github.com/autopkg/recipes",
            }
        }
        mock_get_pref.return_value = mock_recipe_repos

        result = autopkg.get_repo_info("~/Repos/unknown")

        self.assertEqual(result, {})

    @patch("autopkg.get_pref")
    def test_get_repo_info_empty_recipe_repos(self, mock_get_pref):
        """Test get_repo_info when no recipe repos are configured."""
        mock_get_pref.return_value = {}

        result = autopkg.get_repo_info("https://github.com/autopkg/recipes")

        self.assertEqual(result, {})

    @patch("autopkg.get_pref")
    def test_get_repo_info_none_recipe_repos(self, mock_get_pref):
        """Test get_repo_info when RECIPE_REPOS preference is None."""
        mock_get_pref.return_value = None

        result = autopkg.get_repo_info("https://github.com/autopkg/recipes")

        self.assertEqual(result, {})

    @patch("autopkg.get_pref")
    def test_get_repo_info_url_multiple_repos(self, mock_get_pref):
        """Test get_repo_info returns first match when URL matches multiple repos."""
        mock_recipe_repos = {
            "/Users/test/Repos/recipes1": {
                "URL": "https://github.com/autopkg/recipes",
                "branch": "main",
            },
            "/Users/test/Repos/recipes2": {
                "URL": "https://github.com/autopkg/recipes",
                "branch": "dev",
            },
        }
        mock_get_pref.return_value = mock_recipe_repos

        result = autopkg.get_repo_info("https://github.com/autopkg/recipes")

        # Should return first match found
        self.assertIn("path", result)
        self.assertEqual(result["URL"], "https://github.com/autopkg/recipes")
        self.assertIn(
            result["path"], ["/Users/test/Repos/recipes1", "/Users/test/Repos/recipes2"]
        )

    @patch("autopkg.get_pref")
    def test_get_repo_info_repo_without_url(self, mock_get_pref):
        """Test get_repo_info with repo that has no URL field."""
        mock_recipe_repos = {
            "/Users/test/Repos/recipes": {
                "branch": "main",
                # No URL field
            }
        }
        mock_get_pref.return_value = mock_recipe_repos

        result = autopkg.get_repo_info("https://github.com/autopkg/recipes")

        self.assertEqual(result, {})

    @patch("autopkg.get_pref")
    def test_get_repo_info_absolute_path_input(self, mock_get_pref):
        """Test get_repo_info with absolute path input."""
        mock_recipe_repos = {
            "/Users/test/Repos/recipes": {
                "URL": "https://github.com/autopkg/recipes",
                "branch": "main",
            }
        }
        mock_get_pref.return_value = mock_recipe_repos

        with patch("os.path.abspath") as mock_abspath, patch(
            "os.path.expanduser"
        ) as mock_expanduser:
            mock_expanduser.return_value = "/Users/test/Repos/recipes"
            mock_abspath.return_value = "/Users/test/Repos/recipes"

            result = autopkg.get_repo_info("/Users/test/Repos/recipes")

            expected = {
                "path": "/Users/test/Repos/recipes",
                "URL": "https://github.com/autopkg/recipes",
                "branch": "main",
            }
            self.assertEqual(result, expected)

    # Tests for repo management functions
    @patch("autopkg.common_parse")
    @patch("autopkg.gen_common_parser")
    @patch("autopkg.get_search_dirs")
    @patch("autopkg.get_pref")
    @patch("autopkg.expand_repo_url")
    @patch("autopkg.get_recipe_repo")
    @patch("autopkg.save_pref_or_warn")
    @patch("autopkg.log")
    def test_repo_add_success(
        self,
        mock_log,
        mock_save_pref,
        mock_get_recipe_repo,
        mock_expand_repo_url,
        mock_get_pref,
        mock_get_search_dirs,
        mock_gen_parser,
        mock_common_parse,
    ):
        """Test repo_add successfully adding a new repository."""
        # Setup mocks
        mock_parser = Mock()
        mock_gen_parser.return_value = mock_parser
        mock_common_parse.return_value = (Mock(), ["recipes"])
        mock_get_search_dirs.return_value = ["/existing/dir"]
        mock_get_pref.side_effect = lambda key: {
            "RECIPE_REPOS": {},
            "RECIPE_SEARCH_DIRS": ["/existing/dir", "/new/repo/dir"],
        }.get(key, {})
        mock_expand_repo_url.return_value = "https://github.com/autopkg/recipes"
        mock_get_recipe_repo.return_value = "/new/repo/dir"

        result = autopkg.repo_add([None, "repo-add", "recipes"])

        self.assertIsNone(result)  # Function doesn't return on success
        mock_expand_repo_url.assert_called_once_with("recipes")
        mock_get_recipe_repo.assert_called_once_with(
            "https://github.com/autopkg/recipes"
        )
        mock_save_pref.assert_any_call(
            "RECIPE_REPOS",
            {"/new/repo/dir": {"URL": "https://github.com/autopkg/recipes"}},
        )
        mock_log.assert_called()

    @patch("autopkg.save_pref_or_warn")
    @patch("autopkg.get_pref")
    @patch("autopkg.get_search_dirs")
    @patch("autopkg.common_parse")
    @patch("autopkg.gen_common_parser")
    @patch("autopkg.log_err")
    def test_repo_add_no_arguments(
        self,
        mock_log_err,
        mock_gen_parser,
        mock_common_parse,
        mock_get_search_dirs,
        mock_get_pref,
        mock_save_pref,
    ):
        """Test repo_add with no repository arguments."""
        mock_parser = Mock()
        mock_gen_parser.return_value = mock_parser
        mock_common_parse.return_value = (Mock(), [])
        mock_get_search_dirs.return_value = []
        mock_get_pref.return_value = {}

        result = autopkg.repo_add([None, "repo-add"])

        self.assertEqual(result, -1)
        mock_log_err.assert_called_once_with("Need at least one recipe repo URL!")
        # These should not be called since we return early due to no arguments
        mock_save_pref.assert_not_called()

    @patch("autopkg.common_parse")
    @patch("autopkg.gen_common_parser")
    @patch("autopkg.get_search_dirs")
    @patch("autopkg.get_pref")
    @patch("autopkg.expand_repo_url")
    @patch("autopkg.get_recipe_repo")
    @patch("autopkg.save_pref_or_warn")
    @patch("autopkg.log")
    @patch("autopkg.log_err")
    def test_repo_add_file_uri_error(
        self,
        mock_log_err,
        mock_log,
        mock_save_pref,
        mock_get_recipe_repo,
        mock_expand_repo_url,
        mock_get_pref,
        mock_get_search_dirs,
        mock_gen_parser,
        mock_common_parse,
    ):
        """Test repo_add rejects file:// URIs."""
        mock_parser = Mock()
        mock_gen_parser.return_value = mock_parser
        mock_common_parse.return_value = (Mock(), ["file:///local/path"])
        mock_get_search_dirs.return_value = []
        mock_get_pref.return_value = {}

        autopkg.repo_add([None, "repo-add", "file:///local/path"])

        mock_log_err.assert_called_with(
            "AutoPkg does not handle file:// URIs; "
            "add to your local Recipes folder instead."
        )
        mock_get_recipe_repo.assert_not_called()
        # Verify preferences were saved (even though no repos were added)
        mock_save_pref.assert_called()

    @patch("autopkg.common_parse")
    @patch("autopkg.gen_common_parser")
    @patch("autopkg.get_pref")
    @patch("autopkg.get_search_dirs")
    @patch("autopkg.get_repo_info")
    @patch("autopkg.expand_repo_url")
    @patch("autopkg.save_pref_or_warn")
    @patch("autopkg.log")
    @patch("autopkg.log_err")
    @patch("shutil.rmtree")
    def test_repo_delete_success(
        self,
        mock_rmtree,
        mock_log_err,
        mock_log,
        mock_save_pref,
        mock_expand_repo_url,
        mock_get_repo_info,
        mock_get_search_dirs,
        mock_get_pref,
        mock_gen_parser,
        mock_common_parse,
    ):
        """Test repo_delete successfully removing a repository."""
        mock_parser = Mock()
        mock_gen_parser.return_value = mock_parser
        mock_common_parse.return_value = (Mock(), ["recipes"])
        mock_expand_repo_url.return_value = "https://github.com/autopkg/recipes"
        mock_get_repo_info.return_value = {"path": "/repo/path"}
        mock_get_pref.return_value = {
            "/repo/path": {"URL": "https://github.com/autopkg/recipes"}
        }
        mock_get_search_dirs.return_value = ["/repo/path", "/other/path"]

        result = autopkg.repo_delete([None, "repo-delete", "recipes"])

        self.assertIsNone(result)
        mock_expand_repo_url.assert_called_once_with("recipes")
        mock_get_repo_info.assert_called_once_with("https://github.com/autopkg/recipes")
        mock_rmtree.assert_called_once_with("/repo/path")
        mock_log.assert_called_with("Removing repo at /repo/path...")
        mock_save_pref.assert_called()

    @patch("autopkg.common_parse")
    @patch("autopkg.gen_common_parser")
    @patch("autopkg.log_err")
    def test_repo_delete_no_arguments(
        self, mock_log_err, mock_gen_parser, mock_common_parse
    ):
        """Test repo_delete with no repository arguments."""
        mock_parser = Mock()
        mock_gen_parser.return_value = mock_parser
        mock_common_parse.return_value = (Mock(), [])

        result = autopkg.repo_delete([None, "repo-delete"])

        self.assertEqual(result, -1)
        mock_log_err.assert_called_once_with(
            "Need at least one recipe repo path or URL!"
        )

    @patch("autopkg.common_parse")
    @patch("autopkg.gen_common_parser")
    @patch("autopkg.get_pref")
    @patch("autopkg.get_search_dirs")
    @patch("autopkg.get_repo_info")
    @patch("autopkg.expand_repo_url")
    @patch("autopkg.save_pref_or_warn")
    @patch("autopkg.log_err")
    def test_repo_delete_repo_not_found(
        self,
        mock_log_err,
        mock_save_pref,
        mock_expand_repo_url,
        mock_get_repo_info,
        mock_get_search_dirs,
        mock_get_pref,
        mock_gen_parser,
        mock_common_parse,
    ):
        """Test repo_delete when repository is not found."""
        mock_parser = Mock()
        mock_gen_parser.return_value = mock_parser
        mock_common_parse.return_value = (Mock(), ["nonexistent"])
        mock_expand_repo_url.return_value = "https://github.com/autopkg/nonexistent"
        mock_get_repo_info.return_value = {}
        mock_get_pref.return_value = {}
        mock_get_search_dirs.return_value = []

        autopkg.repo_delete([None, "repo-delete", "nonexistent"])

        mock_log_err.assert_called_with(
            "ERROR: Can't find an installed repo for https://github.com/autopkg/nonexistent"
        )
        # Verify preferences were still saved even though repo wasn't found
        mock_save_pref.assert_called()

    @patch("autopkg.common_parse")
    @patch("autopkg.gen_common_parser")
    @patch("autopkg.get_pref")
    @patch("autopkg.get_search_dirs")
    @patch("autopkg.get_repo_info")
    @patch("autopkg.expand_repo_url")
    @patch("autopkg.save_pref_or_warn")
    @patch("autopkg.log")
    @patch("autopkg.log_err")
    @patch("shutil.rmtree")
    def test_repo_delete_rmtree_error(
        self,
        mock_rmtree,
        mock_log_err,
        mock_log,
        mock_save_pref,
        mock_expand_repo_url,
        mock_get_repo_info,
        mock_get_search_dirs,
        mock_get_pref,
        mock_gen_parser,
        mock_common_parse,
    ):
        """Test repo_delete when shutil.rmtree fails."""
        mock_parser = Mock()
        mock_gen_parser.return_value = mock_parser
        mock_common_parse.return_value = (Mock(), ["recipes"])
        mock_expand_repo_url.return_value = "https://github.com/autopkg/recipes"
        mock_get_repo_info.return_value = {"path": "/repo/path"}
        mock_get_pref.return_value = {
            "/repo/path": {"URL": "https://github.com/autopkg/recipes"}
        }
        mock_get_search_dirs.return_value = ["/repo/path"]
        mock_rmtree.side_effect = OSError("Permission denied")

        autopkg.repo_delete([None, "repo-delete", "recipes"])

        mock_log_err.assert_called_with(
            "ERROR: Could not remove /repo/path: Permission denied"
        )
        # Verify preferences were still saved even though rmtree failed
        mock_save_pref.assert_called()

    @patch("autopkg.common_parse")
    @patch("autopkg.gen_common_parser")
    @patch("autopkg.get_pref")
    @patch("builtins.print")
    def test_repo_list_with_repos(
        self, mock_print, mock_get_pref, mock_gen_parser, mock_common_parse
    ):
        """Test repo_list with installed repositories."""
        mock_parser = Mock()
        mock_gen_parser.return_value = mock_parser
        mock_common_parse.return_value = (Mock(), [])
        mock_recipe_repos = {
            "/path/to/recipes": {"URL": "https://github.com/autopkg/recipes"},
            "/path/to/other": {"URL": "https://github.com/user/other-recipes"},
        }
        mock_get_pref.return_value = mock_recipe_repos

        autopkg.repo_list([None, "repo-list"])

        # Check that print was called for both repos plus empty line
        self.assertEqual(mock_print.call_count, 3)
        # Verify that both repos were printed (order might vary but content should be there)
        all_prints = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("other" in print_call for print_call in all_prints))
        self.assertTrue(any("recipes" in print_call for print_call in all_prints))

    @patch("autopkg.common_parse")
    @patch("autopkg.gen_common_parser")
    @patch("autopkg.get_pref")
    @patch("builtins.print")
    def test_repo_list_no_repos(
        self, mock_print, mock_get_pref, mock_gen_parser, mock_common_parse
    ):
        """Test repo_list with no installed repositories."""
        mock_parser = Mock()
        mock_gen_parser.return_value = mock_parser
        mock_common_parse.return_value = (Mock(), [])
        mock_get_pref.return_value = {}

        autopkg.repo_list([None, "repo-list"])

        mock_print.assert_called_once_with("No recipe repos.")

    @patch("autopkg.common_parse")
    @patch("autopkg.gen_common_parser")
    @patch("autopkg.get_pref")
    @patch("autopkg.get_repo_info")
    @patch("autopkg.expand_repo_url")
    @patch("autopkg.run_git")
    @patch("autopkg.log")
    @patch("os.path.abspath")
    @patch("os.path.expanduser")
    def test_repo_update_specific_repo(
        self,
        mock_expanduser,
        mock_abspath,
        mock_log,
        mock_run_git,
        mock_expand_repo_url,
        mock_get_repo_info,
        mock_get_pref,
        mock_gen_parser,
        mock_common_parse,
    ):
        """Test repo_update updating a specific repository."""
        mock_parser = Mock()
        mock_gen_parser.return_value = mock_parser
        mock_common_parse.return_value = (Mock(), ["recipes"])
        mock_expand_repo_url.return_value = "https://github.com/autopkg/recipes"
        mock_get_repo_info.return_value = {"path": "/repo/path"}
        mock_expanduser.return_value = "/repo/path"
        mock_abspath.return_value = "/repo/path"
        mock_run_git.return_value = "Already up to date."

        autopkg.repo_update([None, "repo-update", "recipes"])

        mock_expand_repo_url.assert_called_once_with("recipes")
        mock_get_repo_info.assert_called_once_with("https://github.com/autopkg/recipes")
        mock_run_git.assert_called_once_with(["pull"], git_directory="/repo/path")
        mock_log.assert_any_call("Attempting git pull for /repo/path...")
        mock_log.assert_any_call("Already up to date.")

    @patch("autopkg.common_parse")
    @patch("autopkg.gen_common_parser")
    @patch("autopkg.get_pref")
    @patch("autopkg.run_git")
    @patch("autopkg.log")
    @patch("os.path.abspath")
    @patch("os.path.expanduser")
    def test_repo_update_all_repos(
        self,
        mock_expanduser,
        mock_abspath,
        mock_log,
        mock_run_git,
        mock_get_pref,
        mock_gen_parser,
        mock_common_parse,
    ):
        """Test repo_update updating all repositories."""
        mock_parser = Mock()
        mock_gen_parser.return_value = mock_parser
        mock_common_parse.return_value = (Mock(), ["all"])
        mock_recipe_repos = {
            "/repo/path1": {"URL": "https://github.com/autopkg/recipes"},
            "/repo/path2": {"URL": "https://github.com/user/other"},
        }
        mock_get_pref.return_value = mock_recipe_repos
        mock_expanduser.side_effect = lambda x: x
        mock_abspath.side_effect = lambda x: x
        mock_run_git.return_value = "Already up to date."

        autopkg.repo_update([None, "repo-update", "all"])

        self.assertEqual(mock_run_git.call_count, 2)
        mock_run_git.assert_any_call(["pull"], git_directory="/repo/path1")
        mock_run_git.assert_any_call(["pull"], git_directory="/repo/path2")

    @patch("autopkg.common_parse")
    @patch("autopkg.gen_common_parser")
    @patch("autopkg.log_err")
    def test_repo_update_no_arguments(
        self, mock_log_err, mock_gen_parser, mock_common_parse
    ):
        """Test repo_update with no repository arguments."""
        mock_parser = Mock()
        mock_gen_parser.return_value = mock_parser
        mock_common_parse.return_value = (Mock(), [])

        result = autopkg.repo_update([None, "repo-update"])

        self.assertEqual(result, -1)
        mock_log_err.assert_called_once_with(
            "Need at least one recipe repo path or URL!"
        )

    @patch("autopkg.common_parse")
    @patch("autopkg.gen_common_parser")
    @patch("autopkg.get_repo_info")
    @patch("autopkg.expand_repo_url")
    @patch("autopkg.log_err")
    def test_repo_update_repo_not_found(
        self,
        mock_log_err,
        mock_expand_repo_url,
        mock_get_repo_info,
        mock_gen_parser,
        mock_common_parse,
    ):
        """Test repo_update when repository is not found."""
        mock_parser = Mock()
        mock_gen_parser.return_value = mock_parser
        mock_common_parse.return_value = (Mock(), ["nonexistent"])
        mock_expand_repo_url.return_value = "https://github.com/autopkg/nonexistent"
        mock_get_repo_info.return_value = {}

        autopkg.repo_update([None, "repo-update", "nonexistent"])

        mock_log_err.assert_called_with(
            "ERROR: Can't find an installed repo for https://github.com/autopkg/nonexistent"
        )

    @patch("autopkg.common_parse")
    @patch("autopkg.gen_common_parser")
    @patch("autopkg.get_repo_info")
    @patch("autopkg.expand_repo_url")
    @patch("autopkg.run_git")
    @patch("autopkg.log")
    @patch("autopkg.log_err")
    @patch("os.path.abspath")
    @patch("os.path.expanduser")
    def test_repo_update_git_error(
        self,
        mock_expanduser,
        mock_abspath,
        mock_log_err,
        mock_log,
        mock_run_git,
        mock_expand_repo_url,
        mock_get_repo_info,
        mock_gen_parser,
        mock_common_parse,
    ):
        """Test repo_update when git pull fails."""
        mock_parser = Mock()
        mock_gen_parser.return_value = mock_parser
        mock_common_parse.return_value = (Mock(), ["recipes"])
        mock_expand_repo_url.return_value = "https://github.com/autopkg/recipes"
        mock_get_repo_info.return_value = {"path": "/repo/path"}
        mock_expanduser.return_value = "/repo/path"
        mock_abspath.return_value = "/repo/path"
        git_error = autopkg.GitError("fatal: unable to access")
        mock_run_git.side_effect = git_error

        autopkg.repo_update([None, "repo-update", "recipes"])

        mock_log_err.assert_called_with(git_error)

    @patch("autopkg.common_parse")
    @patch("autopkg.gen_common_parser")
    @patch("autopkg.get_search_dirs")
    @patch("autopkg.get_pref")
    @patch("autopkg.expand_repo_url")
    @patch("autopkg.get_recipe_repo")
    @patch("autopkg.save_pref_or_warn")
    @patch("autopkg.log")
    def test_repo_add_existing_repo_in_search_dirs(
        self,
        mock_log,
        mock_save_pref,
        mock_get_recipe_repo,
        mock_expand_repo_url,
        mock_get_pref,
        mock_get_search_dirs,
        mock_gen_parser,
        mock_common_parse,
    ):
        """Test repo_add when repository is already in search directories."""
        mock_parser = Mock()
        mock_gen_parser.return_value = mock_parser
        mock_common_parse.return_value = (Mock(), ["recipes"])
        mock_get_search_dirs.return_value = ["/existing/repo/dir"]
        mock_get_pref.side_effect = lambda key: {
            "RECIPE_REPOS": {},
            "RECIPE_SEARCH_DIRS": ["/existing/repo/dir"],
        }.get(key, {})
        mock_expand_repo_url.return_value = "https://github.com/autopkg/recipes"
        mock_get_recipe_repo.return_value = "/existing/repo/dir"

        autopkg.repo_add([None, "repo-add", "recipes"])

        # Should not log about adding to search dirs since it's already there
        mock_log.assert_any_call("Updated search path:")
        # But should still add to RECIPE_REPOS
        mock_save_pref.assert_any_call(
            "RECIPE_REPOS",
            {"/existing/repo/dir": {"URL": "https://github.com/autopkg/recipes"}},
        )

    @patch("autopkg.common_parse")
    @patch("autopkg.gen_common_parser")
    @patch("autopkg.get_search_dirs")
    @patch("autopkg.get_pref")
    @patch("autopkg.expand_repo_url")
    @patch("autopkg.get_recipe_repo")
    @patch("autopkg.save_pref_or_warn")
    @patch("autopkg.log")
    def test_repo_add_get_recipe_repo_fails(
        self,
        mock_log,
        mock_save_pref,
        mock_get_recipe_repo,
        mock_expand_repo_url,
        mock_get_pref,
        mock_get_search_dirs,
        mock_gen_parser,
        mock_common_parse,
    ):
        """Test repo_add when get_recipe_repo returns None."""
        mock_parser = Mock()
        mock_gen_parser.return_value = mock_parser
        mock_common_parse.return_value = (Mock(), ["invalid-repo"])
        mock_get_search_dirs.return_value = []
        mock_get_pref.return_value = {}
        mock_expand_repo_url.return_value = "https://github.com/autopkg/invalid-repo"
        mock_get_recipe_repo.return_value = None

        autopkg.repo_add([None, "repo-add", "invalid-repo"])

        # Should still save preferences with empty repos dict
        mock_save_pref.assert_any_call("RECIPE_REPOS", {})
        mock_save_pref.assert_any_call("RECIPE_SEARCH_DIRS", [])


if __name__ == "__main__":
    unittest.main()
