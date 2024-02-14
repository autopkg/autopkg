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


# import imp
# import os
import unittest
from unittest.mock import patch

from autopkglib.common import get_autopkg_version
# import autopkglib
from autopkglib.recipes import Recipe, RecipeChain, TrustBlob


class TestRecipeChain(unittest.TestCase):
    def test_initialization(self):
        recipe_chain = RecipeChain()
        self.assertEqual(recipe_chain.ordered_list_of_recipe_ids, [])
        self.assertEqual(recipe_chain.process, [])
        self.assertEqual(recipe_chain.recipes, [])
        self.assertEqual(recipe_chain.input, {})
        self.assertEqual(recipe_chain.minimum_version, get_autopkg_version())
        self.assertEqual(recipe_chain.ordered_list_of_paths, [])

    # def test_add_recipe(self):
    #     recipe_chain = RecipeChain()
    #     recipe_chain.add_recipe("test_recipe")
    #     self.assertEqual(recipe_chain.ordered_list_of_recipe_ids, ["test_recipe"])
    #     self.assertEqual(recipe_chain.recipes, ["test_recipe"])


class TestRecipe(unittest.TestCase):
    def test_init(self):
        recipe = Recipe()
        self.assertEqual(recipe.shortname, "Recipe.nothing")
        self.assertEqual(recipe.path, "nowhere")
        self.assertEqual(recipe.description, "Base recipe object")
        self.assertEqual(recipe.identifier, "com.github.autopkg.baserecipe")
        self.assertEqual(recipe.minimum_version, "3.0.0")
        self.assertIsNone(recipe.parent_recipe)
        self.assertEqual(recipe.process, [])
        self.assertEqual(recipe.input, {})
        self.assertEqual(recipe.sha256_hash, "abc123")
        self.assertIsNone(recipe.git_hash)
        self.assertFalse(recipe.is_override)
        self.assertIsNone(recipe.trust_info)
        self.assertEqual(recipe.recipe_required_keys, ["Identifier"])
        self.assertEqual(
            recipe.recipe_optional_keys,
            ["Description", "Input", "MinimumVersion", "ParentRecipe", "Process"],
        )
        self.assertEqual(
            recipe.override_required_keys,
            ["Identifier", "Input", "ParentRecipe", "ParentRecipeTrustInfo"],
        )

    @patch("autopkglib.recipes.os.path.isfile")
    @patch("autopkglib.recipes.get_sha256_hash")
    @patch("autopkglib.recipes.get_git_commit_hash")
    @patch("autopkglib.recipes.Recipe._recipe_dict_from_plist")
    @patch("autopkglib.recipes.Recipe.validate")
    @patch("autopkglib.recipes.Recipe._generate_shortname")
    @patch("autopkglib.recipes.Recipe._parse_trust_info")
    def test_from_file(
        self,
        mock_parse_trust_info,
        mock_generate_shortname,
        mock_validate,
        mock_recipe_dict_from_plist,
        mock_get_git_commit_hash,
        mock_get_sha256_hash,
        mock_isfile,
    ):
        mock_isfile.return_value = True
        mock_get_sha256_hash.return_value = "def456"
        mock_get_git_commit_hash.return_value = "123abc"
        mock_recipe_dict_from_plist.return_value = {
            "Identifier": "com.github.autopkg.testrecipe",
            "Description": "Test recipe",
            "Input": {"NAME": "TestRecipe"},
            "MinimumVersion": "1.0.0",
            "Process": [],
            "ParentRecipe": None,
        }
        mock_generate_shortname.return_value = "TestRecipe"

        recipe = Recipe()
        recipe.from_file("test.recipe")

        self.assertEqual(recipe.path, "test.recipe")
        self.assertFalse(recipe.is_override)
        self.assertEqual(recipe.description, "Test recipe")
        self.assertEqual(recipe.identifier, "com.github.autopkg.testrecipe")
        self.assertEqual(recipe.minimum_version, "1.0.0")
        self.assertIsNone(recipe.parent_recipe)
        self.assertEqual(recipe.process, [])
        self.assertEqual(recipe.input, {"NAME": "TestRecipe"})
        self.assertEqual(recipe.sha256_hash, "def456")
        self.assertEqual(recipe.git_hash, "123abc")
        self.assertEqual(recipe.shortname, "TestRecipe")
        self.assertIsNone(recipe.trust_info)

        mock_isfile.assert_called_once_with("test.recipe")
        mock_get_sha256_hash.assert_called_once_with("test.recipe")
        mock_get_git_commit_hash.assert_called_once_with("test.recipe")
        mock_recipe_dict_from_plist.assert_called_once_with("test.recipe")
        mock_validate.assert_called_once_with(
            {
                "Identifier": "com.github.autopkg.testrecipe",
                "Description": "Test recipe",
                "Input": {"NAME": "TestRecipe"},
                "MinimumVersion": "1.0.0",
                "Process": [],
                "ParentRecipe": None,
            }
        )
        mock_generate_shortname.assert_called_once()

    @patch("autopkglib.recipes.pathlib.PurePath")
    @patch("autopkglib.recipes.get_override_dirs")
    def test_check_is_override(self, mock_get_override_dirs, mock_purepath):
        mock_get_override_dirs.return_value = ["/path/to/overrides"]
        mock_purepath.return_value.is_relative_to.return_value = True

        recipe = Recipe()
        result = recipe.check_is_override()

        self.assertTrue(result)
        mock_get_override_dirs.assert_called_once()
        mock_purepath.assert_called_once_with(recipe.path)
        mock_purepath.return_value.is_relative_to.assert_called_once_with(
            "/path/to/overrides"
        )

    def test_recipe_dict_from_yaml(self):
        # TODO: Implement this test
        pass

    def test_recipe_dict_from_plist(self):
        # TODO: Implement this test
        pass

    def test_minimum_version_met(self):
        # TODO: Implement this test
        pass

    def test_valid_recipe_dict_with_keys(self):
        # TODO: Implement this test
        pass

    def test_generate_shortname(self):
        # TODO: Implement this test
        pass


if __name__ == "__main__":
    unittest.main()
