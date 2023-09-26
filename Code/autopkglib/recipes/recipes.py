#!/usr/local/autopkg/python
#
# Copyright 2023 Nick McSpadden
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

import os
import plistlib
from typing import Any, Dict, List, Optional

import yaml
# from autopkglib import log_err


class RecipeError(Exception):
    """Error reading a recipe"""

    pass


class RecipeChain:
    """Full construction of a recipe chain"""

    def __init__(self) -> None:
        """Init"""
        # List of all recipe identifiers that make up this chain
        self.ordered_list_of_recipe_ids = []
        # Final constructed list of all processors
        self.process = []
        # List of recipe objects that made up this chain
        self.recipes = []

    def add_recipe(self, id: str):
        """Add a recipe by identifier into the chain"""
        try:
            recipe = Recipe(id)
        except RecipeError as err:
            print(f"Unable to read recipe at {id}, aborting: {err}")
        self.recipes.append(recipe)
        self.ordered_list_of_recipe_ids.append(id)
        self.process.extend(recipe.process)


class Recipe:
    """A representation of a Recipe"""

    def __init__(self, filename: Optional[str] = None) -> None:
        """All recipes have a generally specific format"""
        # We initialize with empty values, but a successful recipe
        # cannot have these values as empty to execute
        self.description: str = "Base recipe object"
        self.identifier: str = "com.github.autopkg.baserecipe"
        self.minimum_version: str = "3.0.0"
        self.parent_recipe: Optional[str] = None
        # For now, this is a list of dictionaries parsed from the recipe file
        # Should this be converted to an actual list of Processor objects? I don't think
        # we are currently structured in a way to make that reasonable
        self.process: List[Dict[str, Any]] = []
        self.input: Dict[str, str] = {}
        # Defined list of keys that are considered inviolate requirements of a recipe
        self.valid_keys: List[str] = [
            "Description",
            "Identifier",
            "Input",
            "MinimumVersion",
            # "ParentRecipe",  # ParentRecipe is optional, so we'll validate that later
            "Process",
        ]
        if filename:
            self.recipe_from_file(filename)

    def __repr__(self) -> str:
        """String representation of this object"""
        return (
            f'Recipe(Identifier: "{self.identifier}", Description: "{self.description}", '
            f'MinimumVersion: "{self.minimum_version}", ParentRecipe: "{self.parent_recipe}", '
            f'Process: "{self.process}", Input: "{self.input}")'
        )

    def recipe_from_file(self, filename: str) -> None:
        """Read in a recipe from a file path as a str"""
        if not os.path.isfile(filename):
            raise RecipeError(
                f"Provided recipe path is not a readable file: {filename}"
            )
        try:
            if filename.endswith(".yaml"):
                recipe_dict = self._recipe_dict_from_yaml(filename)
            else:
                recipe_dict = self._recipe_dict_from_plist(filename)
        except RecipeError:
            # log_err(f"Unable to read in plist or yaml recipe from {filename}")
            print(f"Unable to read in plist or yaml recipe from {filename}")

        # This will throw an exception if the recipe is invalid
        self.validate(recipe_dict)
        # Assign the values, we'll force some of the variables to become strings
        self.description = str(recipe_dict["Description"])
        self.identifier = str(recipe_dict["Identifier"])
        self.input = recipe_dict["Input"]
        self.minimum_version = str(recipe_dict["MinimumVersion"])
        self.process = recipe_dict["Process"]
        # This is already validated that it must be a string if it exists
        self.parent_recipe = recipe_dict.get("ParentRecipe", None)

    def _recipe_dict_from_yaml(self, filename: str) -> Dict[str, Any]:
        """Read in a dictionary from a YAML file"""
        try:
            # try to read it as yaml
            with open(filename, "rb") as f:
                recipe_dict = yaml.load(f, Loader=yaml.FullLoader)
            return recipe_dict
        except Exception as err:
            raise RecipeError from err

    def _recipe_dict_from_plist(self, filename: str) -> Dict[str, Any]:
        """Read in a dictionary from a plist file"""
        try:
            # try to read it as a plist
            with open(filename, "rb") as f:
                recipe_dict = plistlib.load(f)
            return recipe_dict
        except Exception as err:
            raise RecipeError from err

    def validate(self, recipe_dict: Dict[str, Any]) -> None:
        """Validate that the recipe dictionary contains reasonable and safe values"""
        if not self._valid_recipe_dict_with_keys(recipe_dict):
            raise RecipeError("Recipe did not contain all the required keys!")
        if "ParentRecipe" in recipe_dict and not isinstance(
            recipe_dict["ParentRecipe"], str
        ):
            raise RecipeError("ParentRecipe must be a string")

    def _valid_recipe_dict_with_keys(self, recipe_dict) -> bool:
        """Attempts to read a dict and ensures the keys in
        keys_to_verify exist. Returns False on any failure, True otherwise."""
        if recipe_dict:
            for key in self.valid_keys:
                if key not in recipe_dict:
                    return False
            # if we get here, we found all the keys
            return True
        return False


if __name__ == "__main__":
    recipe = Recipe("/Users/nmcspadden/Library/AutoPkg/RecipeRepos/com.github.autopkg.recipes/GoogleChrome/GoogleChromePkg.download.recipe")
    print(recipe)
    recipe = Recipe()
    recipe.recipe_from_file("/Users/nmcspadden/Library/AutoPkg/RecipeRepos/com.github.autopkg.recipes/GoogleChrome/GoogleChromePkg.pkg.recipe")
    print(recipe)
    recipe = Recipe()
    recipe.recipe_from_file("/Users/nmcspadden/Documents/GitHub/autopkg/Code/tests/Test-Recipes/AutopkgCore.test.recipe.yaml")
    print(recipe)
