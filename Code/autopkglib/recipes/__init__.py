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

import glob
import json
import os
import pathlib
import plistlib
import pprint
import sys
from dataclasses import dataclass, field
from typing import Any, Optional

import yaml
from autopkglib.apgit import get_git_commit_hash
from autopkglib.common import (
    DEFAULT_RECIPE_MAP,
    DEFAULT_SEARCH_DIRS,
    RECIPE_EXTS,
    get_autopkg_version,
    get_sha256_hash,
    log,
    log_err,
    version_equal_or_greater,
)
from autopkglib.prefs import get_override_dirs, get_pref

# Set the global recipe map
globalRecipeMap: dict[str, dict[str, str]] = {
    "identifiers": {},
    "shortnames": {},
    "overrides": {},
    "overrides-identifiers": {},
}

# Historically, recipes were treated as simple Python dictionaries. This made sense because Pyobjc gave us a natural
# toll-free bridge to convert between Plists and Python dictionaries. Recipes were essentially parsed into dictionaries
# and everything was treated as functionally strings.
#
# However, there are many problems with this approach. For one thing, plists can nest dicts and that makes type checking
# in particular rather challenging and unwieldy. It's flexible, but the lack of type safety is one of the big design
# limitations in AutoPkg's error-handling. AutoPkg basically can't produce meaningful error messages at runtime because
# it can't realistically predict what types of data it's getting from a plist.
#
# To address this general problem and allow AutoPkg to more safely handle different scenarios, we're going to reduce
# the flexibility a bit by instead converting Recipes and their contents into actual objects.
#
# Generally speaking, all Recipes follow a specific structure and have generally immutable top level keys. By
# turning this into classes, we can guarantee the keys we care about exist, and we can type-check the values to
# validate a recipe will be safe to run before we even do anything about it. This will allow AutoPkg to expose much
# more meaningful error modes to the operator rather than just Python stacketraces.
#
# Recipe Trust info, a unique feature of overrides, is now using Python 3.7's dataclasses feature. Dataclasses
# are mutable namedtuples, which themselves are like mini-objects that have named attributes. Since we're never going
# to add arbitrary keys to these objects, they're a perfect fit for this use case. Parent Trust always has a fixed
# representation.


class RecipeError(Exception):
    """Error reading a recipe"""

    pass


class RecipeNotFoundError(RecipeError):
    """Error finding a recipe"""

    pass


class RecipeMinimumVersionNotMetError(RecipeError):
    """Recipe requires a newer version than we are running"""

    pass


# Use Dataclasses to represent Trust content because they are always fixed structures
@dataclass
class TrustBlob:
    """Represent the parent trust information of a recipe aspect.

    In plists, this is represented as:
    <dict>
        <key>git_hash</key>
        <string>a28e56e90ebc52512a4b7ec8fe1981bf02e92bc5</string>
        <key>path</key>
        <string>~/Library/AutoPkg/RecipeRepos/com.github.autopkg.recipes/Mozilla/MozillaURLProvider.py</string>
        <key>sha256_hash</key>
        <string>c4ce035b1a629c4925a80003899fcf39480e5224b3015613440f07ab96211f17</string>
    </dict>

    This cannot be initialized with no arguments, and must be filled on instantiation:
    non_core_processor = TrustBlob(
        git_hash=recipe_dict["ParentRecipeTrustInfo"]["non_core_processors"][some_key]["git_hash"],
        path=recipe_dict["ParentRecipeTrustInfo"]["non_core_processors"][some_key]["path"],
        sha256_hash=recipe_dict["ParentRecipeTrustInfo"]["non_core_processors"][some_key]["sha256_hash"],
    )
    """

    git_hash: str
    path: str
    sha256_hash: str


# Similarly, the entire ParentRecipeTrustInfo dictionary is always fixed
@dataclass
class ParentRecipeTrustInfo:
    """Represent the parent trust information of a recipe
    This can be instantiated with no arguments and filled later:
        trust = ParentRecipeTrustInfo()
        trust.update(
            {"non_core_processors": {"ProcessorName": TrustBlob(...)},
            "parent_recipes": {"RecipeName": TrustBlob(...)}}
        )
    However, this does not validate that the trust has been filled correctly. Using unfilled trust info will
    fail trust validation.
    """

    non_core_processors: dict[str, TrustBlob] = field(default_factory=dict)
    parent_recipes: dict[str, TrustBlob] = field(default_factory=dict)


class RecipeChain:
    """Full construction of a recipe chain"""

    def __init__(self) -> None:
        """Create a full chain of recipes. Add recipes with add_recipe(),
        then compile with build()"""
        # List of all recipe identifiers that make up this chain
        self.ordered_list_of_recipe_ids: list[str] = []
        # Final constructed list of all processors
        self.process: list[dict[str, Any]] = []
        # List of recipe objects that made up this chain
        # The recipe chain's list of recipes is reverse-ordered
        # i.e. item 0 is the "root" recipe with no parents
        self.recipes: list[Recipe] = []
        # The amalgamated inputs
        self.input: dict[str, str] = {}
        # Minimum version by default starts at our version
        self.minimum_version: str = get_autopkg_version()
        # List of all recipe paths in the chain
        self.ordered_list_of_paths: list[str] = []

    def add_recipe(self, path: str) -> None:
        """Add a recipe by path into the chain"""
        try:
            recipe = Recipe(path)
        except RecipeError as err:
            print(f"Unable to read recipe at {path}, aborting: {err}")
            raise
        # Add to the recipe parent lists
        self.ordered_list_of_recipe_ids.append(recipe.identifier)
        self.ordered_list_of_paths.append(recipe.path)
        # Add to the recipe object list
        self.recipes.append(recipe)
        # Look for parents and add them to the chain
        if recipe.parent_recipe:
            if recipe.parent_recipe in self.ordered_list_of_recipe_ids:
                log_err(
                    "WARNING! You have a circular parental reference! This identifier has already been processed!"
                )
                raise RecipeError("Circular dependency")
            try:
                # parent_recipe = fetch_recipe(recipe.parent_recipe)
                parent_recipe_path = find_recipe_path(
                    recipe.parent_recipe,
                    make_suggestions=False,
                    search_github=False,
                    auto_pull=False,
                    skip_overrides=True,
                )
            except RecipeError as err:
                print(
                    f"Unable to find parent recipe {recipe.parent_recipe}, aborting: {err}"
                )
                raise
            self.add_recipe(parent_recipe_path)

    def build(self, check_only: bool = False) -> None:
        """Compile and build the whole recipe chain"""
        # Reverse the order of the ids and recipes, and then build the process list
        self.ordered_list_of_recipe_ids.reverse()
        self.recipes.reverse()
        for recipe in self.recipes:
            self.input.update(recipe.input)
            self.process.extend(recipe.process)
            # Set our minimum version to the highest we see
            if version_equal_or_greater(self.minimum_version, recipe.minimum_version):
                self.minimum_version = recipe.minimum_version
        if check_only:
            self.process = self.get_check_only_processors()

    def add_preprocessor(self, processor: dict[str, Any]) -> None:
        """Add a preprocessor to the beginning of the process list of a chain."""
        self.process.insert(0, processor)

    def add_postprocessor(self, processor: dict[str, Any]) -> None:
        """Add a postrocessor to the end of the process list of a chain."""
        self.process.append(processor)

    def get_check_only_processors(self) -> list[dict[str, Any]]:
        """Return a list of processors up until EndOfCheckPhase"""
        list_of_processors = [x["Processor"] for x in self.process]
        check_index = list_of_processors.index("EndOfCheckPhase")
        return self.process[0 : check_index + 1]

    def display_chain(self) -> None:
        """Print out the whole chain"""
        print("Minimum version:")
        print(f"  {self.minimum_version}")
        print("Recipe Chain:")
        for recipe in self.recipes:
            print(
                f"\t{recipe.identifier}:\n"
                f"\t\tSHA256: {recipe.sha256_hash}\n"
                f"\t\tGit Hash: {recipe.git_hash}"
            )
        print("Inputs:")
        pprint.pprint(self.input, indent=2, width=1)
        print("Processors:")
        for processor in self.process:
            print(f"  {processor}")

    def to_dict(self, check_only: bool = False) -> dict[str, Any]:
        """Return a dictionary representation of the chain"""
        process = self.process
        if check_only:
            process = self.get_check_only_processors()
        return {
            "Input": self.input,
            "MinimumVersion": self.minimum_version,
            "Process": process,
        }

    def verify_trust(self) -> bool:
        """Return True if the recipe trust is correct."""
        return True
        # TODO: Implement this
        # We need to determine if a recipe in the chain is an override and thus contains trust
        # if it contains trust, we then go validate that the trust is correct
        # if there are no overrides, this always returns True (but maybe we print out that we did nothing)
        # for recipe in self.recipes:


class Recipe:
    """A representation of a Recipe"""

    def __init__(self, filename: Optional[str] = None, for_map: bool = False) -> None:
        """All recipes have a generally specific format"""
        self.shortname: str = "Recipe.nothing"
        self.path: str = "nowhere"
        # We initialize with empty values, but a successful recipe
        # cannot have these values as empty to execute
        self.description: str = "Base recipe object"
        self.identifier: str = "com.github.autopkg.baserecipe"
        self.minimum_version: str = "3.0.0"
        self.parent_recipe: Optional[str] = None
        # For now, this is a list of dictionaries parsed from the recipe file
        # Should this be converted to an actual list of Processor objects? I don't think
        # we are currently structured in a way to make that reasonable
        self.process: list[Optional[dict[str, Any]]] = []
        self.input: dict[str, str] = {}
        # Trust-specific values
        self.sha256_hash: str = "abc123"
        self.git_hash: Optional[str] = None
        # Override-specific functionality
        self.is_override: bool = False
        self.trust_info: Optional[ParentRecipeTrustInfo] = None
        # Defined list of keys that are considered inviolate requirements of a recipe
        self.recipe_required_keys: list[str] = [
            "Identifier",
        ]
        self.recipe_optional_keys: list[str] = [
            "Description",
            "Input",
            "MinimumVersion",
            "ParentRecipe",
            "Process",
        ]
        self.override_required_keys: list[str] = [
            "Identifier",
            "Input",
            "ParentRecipe",
            "ParentRecipeTrustInfo",
        ]
        if filename:
            self.from_file(filename, for_map)

    def __repr__(self) -> str:
        """String representation of this object"""
        return (
            f'Recipe(Identifier: "{self.identifier}", IsOverride: "{self.is_override}", '
            f'Description: "{self.description}", '
            f'MinimumVersion: "{self.minimum_version}", ParentRecipe: "{self.parent_recipe}", '
            f'Process: "{self.process}", Input: "{self.input}", '
            f'Shortname: "{self.shortname}", Full path: "{self.path}")'
        )

    def from_file(self, filename: str, for_map: bool = False) -> None:
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

        self.path = filename
        # Is this an override?
        self.is_override = self.check_is_override()
        # This will throw an exception if the recipe is invalid
        self.validate(recipe_dict)
        self.shortname = self._generate_shortname()
        if self.is_override:
            # Trust info is only present in overrides
            self._parse_trust_info(recipe_dict)
        # Assign the values, we'll force some of the variables to become strings
        if not for_map:
            self.sha256_hash = get_sha256_hash(self.path)
            self.git_hash = get_git_commit_hash(self.path)
        self.description = str(recipe_dict.get("Description", ""))
        # The identifier is the only field we cannot live without
        self.identifier = str(recipe_dict["Identifier"])
        self.input = recipe_dict.get("Input", {"NAME": self.shortname})
        self.minimum_version = str(recipe_dict.get("MinimumVersion", "1.0.0"))
        self.process = recipe_dict.get("Process", [])
        # This is already validated that it must be a string if it exists
        self.parent_recipe = recipe_dict.get("ParentRecipe", None)

    def _parse_trust_info(self, recipe_dict: [dict[str, Any]]) -> None:
        """Parse the trust info from a recipe dictionary"""
        trust = ParentRecipeTrustInfo()
        for proc in (
            recipe_dict["ParentRecipeTrustInfo"].get("non_core_processors", {}).keys()
        ):
            proc_trust = TrustBlob(
                git_hash=recipe_dict["ParentRecipeTrustInfo"]["non_core_processors"][
                    proc
                ]["git_hash"],
                path=recipe_dict["ParentRecipeTrustInfo"]["non_core_processors"][proc][
                    "path"
                ],
                sha256_hash=recipe_dict["ParentRecipeTrustInfo"]["non_core_processors"][
                    proc
                ]["sha256_hash"],
            )
            trust.non_core_processors.update({str(proc): proc_trust})
        for parent_recipe in (
            recipe_dict["ParentRecipeTrustInfo"].get("parent_recipes", {}).keys()
        ):
            rec_trust = TrustBlob(
                git_hash=recipe_dict["ParentRecipeTrustInfo"]["parent_recipes"][
                    parent_recipe
                ]["git_hash"],
                path=recipe_dict["ParentRecipeTrustInfo"]["parent_recipes"][
                    parent_recipe
                ]["path"],
                sha256_hash=recipe_dict["ParentRecipeTrustInfo"]["parent_recipes"][
                    parent_recipe
                ]["sha256_hash"],
            )
            trust.parent_recipes.update({str(parent_recipe): rec_trust})
        self.trust_info = trust

    def check_is_override(self) -> bool:
        """Return True if this recipe is an override"""
        # Recipe overrides must be stored in the Overrides directories
        path = pathlib.PurePath(self.path)
        for override_dir in get_override_dirs():
            if path.is_relative_to(override_dir):
                return True
        return False

    def _recipe_dict_from_yaml(self, filename: str) -> dict[str, Any]:
        """Read in a dictionary from a YAML file"""
        try:
            # try to read it as yaml
            with open(filename, "rb") as f:
                recipe_dict = yaml.load(f, Loader=yaml.FullLoader)
            return recipe_dict
        except Exception as err:
            raise RecipeError from err

    def _recipe_dict_from_plist(self, filename: str) -> dict[str, Any]:
        """Read in a dictionary from a plist file"""
        try:
            # try to read it as a plist
            with open(filename, "rb") as f:
                recipe_dict = plistlib.load(f)
            return recipe_dict
        except Exception as err:
            raise RecipeError from err

    def _minimum_version_met(self) -> bool:
        """Returns True if the version provided meets the minimum version requirement"""
        return version_equal_or_greater(get_autopkg_version(), self.minimum_version)

    def validate(self, recipe_dict: dict[str, Any]) -> None:
        """Validate that the recipe dictionary contains reasonable and safe values"""
        required_keys = self.recipe_required_keys
        if self.is_override:
            # We only validate that the required keys for overrides are present
            # We aren't verifying trust at this point
            required_keys = self.override_required_keys
        if not self._valid_recipe_dict_with_keys(recipe_dict, required_keys):
            raise RecipeError("Recipe did not contain all the required keys!")
        if "ParentRecipe" in recipe_dict and not isinstance(
            recipe_dict["ParentRecipe"], str
        ):
            raise RecipeError("ParentRecipe must be a string")
        recipe_mininum_vers = str(recipe_dict.get("MinimumVersion", "1.0.0"))
        self.minimum_version = recipe_mininum_vers
        # Check our minimum version
        if not self._minimum_version_met():
            raise RecipeMinimumVersionNotMetError(
                f"Recipe requires a minimum version of {recipe_dict['MinimumVersion']}, "
                f"but we are running {get_autopkg_version()}"
            )

    def _valid_recipe_dict_with_keys(
        self, recipe_dict: dict[str, Any], keys_to_verify: list[str]
    ) -> bool:
        """Attempts to read a dict and ensures the keys in
        keys_to_verify exist. Returns False on any failure, True otherwise."""
        missing_keys = []
        if recipe_dict:
            for key in keys_to_verify:
                if key not in recipe_dict:
                    missing_keys.append(key)
        if missing_keys:
            log_err(f"Recipe is missing some keys: {', '.join(missing_keys)}")
            return False
        # if we get here, we found all the keys
        return True

    def _generate_shortname(self) -> str:
        """Removes supported recipe extensions from a filename or path.
        If the filename or path does not end with any known recipe extension,
        the name is returned as is."""
        name = os.path.basename(self.path)
        for ext in RECIPE_EXTS:
            if name.endswith(ext):
                return name[: -len(ext)]
        return name


def calculate_recipe_map(
    extra_search_dirs: Optional[list[str]] = None,
    extra_override_dirs: Optional[list[str]] = None,
    skip_cwd: bool = True,
):
    """Recalculate the entire recipe map"""
    global globalRecipeMap
    globalRecipeMap = {
        "identifiers": {},
        "shortnames": {},
        "overrides": {},
        "overrides-identifiers": {},
    }
    # If extra search paths were provided as CLI arguments, let's search those too
    if extra_search_dirs is None:
        extra_search_dirs = []
    if extra_override_dirs is None:
        extra_override_dirs = []
    search_dirs = get_pref("RECIPE_SEARCH_DIRS") or DEFAULT_SEARCH_DIRS
    for search_dir in search_dirs + extra_search_dirs:
        if search_dir == "." and skip_cwd:
            # skip searching cwd and don't add it to the map
            continue
        elif search_dir == ".":
            # if we're not skipping cwd, we want to add it to the map
            search_dir = os.path.abspath(".")
        globalRecipeMap["identifiers"].update(
            map_key_to_paths("identifiers", search_dir)
        )
        globalRecipeMap["shortnames"].update(map_key_to_paths("shortnames", search_dir))
    # Do overrides separately
    for override in get_override_dirs() + extra_override_dirs:
        globalRecipeMap["overrides"].update(map_key_to_paths("overrides", override))
        globalRecipeMap["overrides-identifiers"].update(
            map_key_to_paths("overrides-identifiers", override)
        )
    if skip_cwd and (not extra_search_dirs or not extra_override_dirs):
        # Don't store the extra stuff in the cache; they're intended to be temporary
        write_recipe_map_to_disk()


def map_key_to_paths(keyname: str, repo_dir: str) -> dict[str, str]:
    """Return a dict of keyname to absolute recipe paths"""
    recipe_map = {}
    normalized_dir = os.path.abspath(os.path.expanduser(repo_dir))
    patterns = [os.path.join(normalized_dir, f"*{ext}") for ext in RECIPE_EXTS]
    patterns.extend([os.path.join(normalized_dir, f"*/*{ext}") for ext in RECIPE_EXTS])
    for pattern in patterns:
        matches = glob.glob(pattern)
        for match in matches:
            try:
                # We need to load and validate the recipe in order to extract the identifier
                recipe = Recipe(match, for_map=False)
            except RecipeError as err:
                print(
                    f"WARNING: {match} is potentially an invalid file, not adding it to the recipe map! "
                    "Please file a GitHub Issue for this repo. "
                    f"Original error: {err}"
                )
                continue
            key = recipe.shortname
            if "identifiers" in keyname:
                key = recipe.identifier
            if key in recipe_map or key in globalRecipeMap[keyname]:
                # we already have this recipe, don't update it
                continue
            recipe_map[key] = match
    return recipe_map


def write_recipe_map_to_disk():
    """Write the recipe map to disk"""
    local_recipe_map = {}
    local_recipe_map.update(globalRecipeMap)
    with open(DEFAULT_RECIPE_MAP, "w") as f:
        json.dump(
            local_recipe_map,
            f,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )


def handle_reading_recipe_map_file() -> dict[str, dict[str, str]]:
    """Read the recipe map file, handle exceptions"""
    try:
        with open(DEFAULT_RECIPE_MAP, "r") as f:
            recipe_map = json.load(f)
    except (OSError, json.decoder.JSONDecodeError):
        log_err("Cannot read the recipe map file!")
        return {}
    return recipe_map


def validate_recipe_map(recipe_map: dict[str, dict[str, str]]) -> bool:
    """Return True if the recipe map has the correct set of keys"""
    expected_keys = [
        "identifiers",
        "overrides",
        "overrides-identifiers",
        "shortnames",
    ]
    if set(expected_keys).issubset(recipe_map.keys()):
        return True
    return False


def read_recipe_map(rebuild: bool = False, allow_continuing: bool = False) -> None:
    """Parse the recipe map JSON file and update the global Recipe Map object.
    If rebuild is True, rebuild the map. If allow_continuing is True, don't exit"""
    global globalRecipeMap
    recipe_map = handle_reading_recipe_map_file()
    if validate_recipe_map(recipe_map):
        globalRecipeMap.update(recipe_map)
    else:
        if rebuild:
            log("Cannot find or read the recipe map! Creating it now...")
            calculate_recipe_map()
        elif not rebuild and not allow_continuing:
            log(
                "Cannot parse the recipe map - it's either missing or invalid!"
                "\nTry adding or removing a repo to rebuild it."
            )
            sys.exit(1)


def find_recipe_path(
    input: str,
    make_suggestions: bool = True,
    search_github: bool = True,
    auto_pull: bool = False,
    skip_overrides: bool = False,  # In case we know ahead of time we're not looking for an override
) -> str:
    """Return file path to the input, raise exception if it can't find it"""
    # Locates a recipe from path, shortname, or identifier. If the input is the pathname to a file on disk,
    # we attempt to load that file and use it as recipe.
    # Otherwise, we treat input as a recipe name or identifier and search the map. If we don't find it,
    # rebuild the map with CWD and search again. Raise an exception if we still don't find it.
    if os.path.isfile(input):
        log("Found recipe at path")
        # We're not validating that this is actually a real recipe at this point, that happens later
        return input
    # Okay, not a file, let's look for it in the map
    recipe_path: str = find_recipe_in_map(input, skip_overrides)
    if recipe_path:
        # Found it, load the recipe and send it back
        return recipe_path
    # If we still didn't find it in the map, try rebuilding the map with current dirs
    log(
        "Didn't find recipe in map, rebuilding recipe map with current working directories..."
    )
    calculate_recipe_map(skip_cwd=False)
    recipe_path: str = find_recipe_in_map(input, skip_overrides)
    if recipe_path:
        # Found it, load the recipe and send it back
        return recipe_path

    # TODO: Everything after this is related to making suggestions, or searching GitHub
    # We didn't find the recipe, so let's ask Github for suggestions
    # if not recipe_path and make_suggestions:
    #     make_suggestions_for(input)

    # BAIL!
    raise RecipeNotFoundError(input)


def fetch_recipe_chain(
    input: str,
    make_suggestions: bool = True,
    search_github: bool = True,
    auto_pull: bool = False,
    skip_overrides: bool = False,
    check_only: bool = False,
) -> RecipeChain:
    """Obtain a RecipeChain object from an input string. Does not handle exceptions."""
    recipe_path = find_recipe_path(
        input, make_suggestions, search_github, auto_pull, skip_overrides
    )
    chain = RecipeChain()
    chain.add_recipe(recipe_path)
    chain.build(check_only)
    return chain


def fetch_recipe(
    input: str,
    make_suggestions: bool = True,
    search_github: bool = True,
    auto_pull: bool = False,
    skip_overrides: bool = False,
) -> Recipe:
    """Obtain a Recipe object from an input string. Does not handle exceptions."""
    # Look in the map, rebuild if necessary
    recipe_path = find_recipe_path(
        input, make_suggestions, search_github, auto_pull, skip_overrides
    )
    return Recipe(recipe_path)


def find_recipe_in_map(id_or_name: str, skip_overrides: bool = False) -> Optional[str]:
    """Find a recipe path from the map based on input that might be an identifier
    or a name"""
    # The recipe search should allow searching overrides vs. not (make-overrides shouldn't
    # search overrides first)
    # When searching:
    # Search for shortname in overrides first, since that's most common
    # Search for an override identifier
    # Search in shortnames
    # Search in identifiers
    # oh noez we can't find it
    log(f"Looking for {id_or_name}...")
    recipe_path = find_recipe_by_name_in_map(
        id_or_name, skip_overrides
    ) or find_recipe_by_id_in_map(id_or_name, skip_overrides)
    if recipe_path:
        return recipe_path
    # At this point, we didn't find the recipe in the map
    log(f"Did not find {id_or_name} in recipe map")
    return None


def find_recipe_by_id_in_map(
    identifier: str, skip_overrides: bool = False
) -> Optional[str]:
    """Search recipe map for an identifier"""
    if not skip_overrides and identifier in globalRecipeMap.get(
        "overrides-identifiers", {}
    ):
        log(f"Found {identifier} in recipe map overrides")
        return globalRecipeMap["overrides-identifiers"][identifier]
    if identifier in globalRecipeMap["identifiers"]:
        log(f"Found {identifier} in recipe map")
        return globalRecipeMap["identifiers"][identifier]
    return None


def find_recipe_by_name_in_map(
    name: str, skip_overrides: bool = False
) -> Optional[str]:
    """Search recipe map for a shortname"""
    # Check the overrides first, unless skipping them
    if not skip_overrides and name in globalRecipeMap["overrides"]:
        log(f"Found {name} in recipe map overrides")
        return globalRecipeMap["overrides"][name]
    # search by "Name" in the recipe map
    if name in globalRecipeMap["shortnames"]:
        log(f"Found {name} in recipe map")
        return globalRecipeMap["shortnames"][name]
    return None


def find_name_from_identifier(identifier: str) -> Optional[str]:
    """Find a recipe name from its identifier"""
    # TODO: change this to Recipe object
    recipe_path = globalRecipeMap["identifiers"].get(identifier)
    for shortname, path in globalRecipeMap["shortnames"].items():
        if recipe_path == path:
            return shortname
    log_err(f"Could not find shortname from {identifier}!")
    return None


def find_identifier_from_name(name: str) -> Optional[str]:
    """Find a recipe identifier from its shortname"""
    # TODO: change this to Recipe object
    recipe_path = globalRecipeMap["shortnames"].get(name)
    for id, path in globalRecipeMap["identifiers"].items():
        if recipe_path == path:
            return id
    log_err(f"Could not find identifier from {name}!")
    return None
