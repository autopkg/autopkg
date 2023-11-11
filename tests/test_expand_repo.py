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

from autopkg import autopkg


class TestExpandRepo(unittest.TestCase):
    """Test cases for expansion of recipe repos for add/delete/update."""

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


if __name__ == "__main__":
    unittest.main()
