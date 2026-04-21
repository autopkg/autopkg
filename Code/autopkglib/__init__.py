#!/usr/local/autopkg/python
#
# Copyright 2010 Per Olofsson
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

"""Core/shared autopkglib functions"""

import glob
import importlib.resources
import importlib.util
import json
import os
import plistlib
import pprint
import re
import subprocess
import sys
import traceback
from copy import deepcopy
from distutils.version import LooseVersion
from typing import IO, Any, Union

import appdirs
import yaml

# Type for methods that accept either a filesystem path or a file-like object.
FileOrPath = Union[IO, str, bytes, int]

# Type for ubiquitous dictionary type used throughout autopkg.
# Most commonly for `input_variables` and friends. It also applies to virtually all
# usages of plistlib results as well.
VarDict = dict[str, Any]


def is_mac() -> bool:
    """Return True if current OS is macOS."""
    return "darwin" in sys.platform.lower()


def is_windows() -> bool:
    """Return True if current OS is Windows."""
    return "win32" in sys.platform.lower()


def is_linux() -> bool:
    """Return True if current OS is Linux."""
    return "linux" in sys.platform.lower()


def log(msg, error=False) -> None:
    """Message logger, prints to stdout/stderr."""
    if error:
        print(msg, file=sys.stderr)
    else:
        print(msg)


def log_err(msg) -> None:
    """Message logger for errors."""
    log(msg, error=True)


try:
    from CoreFoundation import (
        CFPreferencesAppSynchronize,
        CFPreferencesCopyAppValue,
        CFPreferencesCopyKeyList,
        CFPreferencesSetAppValue,
        kCFPreferencesAnyHost,
        kCFPreferencesAnyUser,
        kCFPreferencesCurrentHost,
        kCFPreferencesCurrentUser,
    )
    from Foundation import NSArray, NSDictionary, NSNumber
except ImportError:
    if is_mac():
        print(
            "ERROR: Failed 'from Foundation import NSArray, NSDictionary' in "
            + __name__
        )
        print(
            "ERROR: Failed 'from CoreFoundation import "
            "CFPreferencesAppSynchronize, ...' in " + __name__
        )
        raise
    # On non-macOS platforms, the above imported names are stubbed out.
    NSArray = list
    NSDictionary = dict
    NSNumber = int

    def CFPreferencesAppSynchronize(*args, **kwargs):
        pass

    def CFPreferencesCopyAppValue(*args, **kwargs):
        pass

    def CFPreferencesCopyKeyList(*args, **kwargs):
        return []

    def CFPreferencesSetAppValue(*args, **kwargs):
        pass

    kCFPreferencesAnyHost = None
    kCFPreferencesAnyUser = None
    kCFPreferencesCurrentUser = None
    kCFPreferencesCurrentHost = None

APP_NAME = "Autopkg"
BUNDLE_ID = "com.github.autopkg"

RE_KEYREF = re.compile(r"%(?P<key>[a-zA-Z_][a-zA-Z_0-9]*)%")

# Supported recipe extensions
RECIPE_EXTS = (".recipe", ".recipe.plist", ".recipe.yaml")

# Default filesystem locations used by autopkg. These mirror the post-3.x
# layout so that the recipe map backport can find the same paths that the
# dev-3.x code expects.
DEFAULT_USER_LIBRARY_DIR = "~/Library/AutoPkg"
DEFAULT_LIBRARY_DIR = "/Library/AutoPkg"
DEFAULT_USER_OVERRIDES_DIR = os.path.join(DEFAULT_USER_LIBRARY_DIR, "RecipeOverrides")
DEFAULT_USER_RECIPES_DIR = os.path.join(DEFAULT_USER_LIBRARY_DIR, "Recipes")
DEFAULT_USER_CACHE_DIR = os.path.join(DEFAULT_USER_LIBRARY_DIR, "Cache")
DEFAULT_USER_REPOS_DIR = os.path.join(DEFAULT_USER_LIBRARY_DIR, "RecipeRepos")
# Canonical on-disk location of the recipe map
DEFAULT_RECIPE_MAP = os.path.join(DEFAULT_USER_LIBRARY_DIR, "recipe_map.json")
DEFAULT_GH_TOKEN = os.path.join(DEFAULT_USER_LIBRARY_DIR, "gh_token")
DEFAULT_SEARCH_DIRS = [".", DEFAULT_USER_LIBRARY_DIR, DEFAULT_LIBRARY_DIR]


def autopkg_user_folder() -> str:
    """Return the absolute path to the user's AutoPkg folder.

    The folder is created on demand when possible, but we fail soft on
    permission or read-only errors so callers running in sandboxed or
    mocked environments (notably the test suite, which routinely patches
    ``os.path.expanduser`` to point at ``/``) are not crashed by a
    housekeeping operation.

    Note: any ``OSError`` raised during directory creation is swallowed
    here and surfaces later at the actual write site — see
    ``write_recipe_map_to_disk`` which handles real write failures."""
    folder = os.path.abspath(os.path.expanduser(DEFAULT_USER_LIBRARY_DIR))
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        pass
    return folder


class PreferenceError(Exception):
    """Preference exception"""

    pass


class Preferences:
    """An abstraction to hold all preferences."""

    def __init__(self):
        """Init."""
        self.prefs: VarDict = {}
        # What type of preferences input are we using?
        self.type: str | None = None
        # Path to the preferences file we were given
        self.file_path: str | None = None
        # If we're on macOS, read in the preference domain first.
        if is_mac():
            self.prefs = self._get_macos_prefs()
        else:
            self.prefs = self._get_file_prefs()
        if not self.prefs:
            log_err("WARNING: Did not load any default preferences.")

    def _parse_json_or_plist_file(self, file_path) -> VarDict:
        """Parse the file. Start with plist, then JSON."""
        try:
            with open(file_path, "rb") as f:
                data = plistlib.load(f)
            self.type = "plist"
            self.file_path = file_path
            return data
        except Exception:
            pass
        try:
            with open(file_path, "rb") as f:
                data = json.load(f)
                self.type = "json"
                self.file_path = file_path
                return data
        except Exception:
            pass
        return {}

    def __deepconvert_objc(self, obj) -> Any:
        """Convert all contents of an ObjC object to Python primitives."""
        value = obj
        if isinstance(obj, NSNumber):
            value = int(obj)
        elif isinstance(obj, NSArray) or isinstance(obj, list):
            value = [self.__deepconvert_objc(x) for x in obj]
        elif isinstance(obj, NSDictionary):
            value = dict(obj)
            # RECIPE_REPOS is a dict of dicts
            for k, v in value.items():
                if isinstance(v, NSDictionary):
                    value[k] = dict(v)
        else:
            return obj
        return value

    def _get_macos_pref(self, key) -> Any:
        """Get a specific macOS preference key."""
        value = self.__deepconvert_objc(CFPreferencesCopyAppValue(key, BUNDLE_ID))
        return value

    def _get_macos_prefs(self) -> VarDict:
        """Return a dict (or an empty dict) with the contents of all
        preferences in the domain."""
        prefs = {}

        # get keys stored via 'defaults write [domain]'
        user_keylist = CFPreferencesCopyKeyList(
            BUNDLE_ID, kCFPreferencesCurrentUser, kCFPreferencesAnyHost
        )

        # get keys stored via 'defaults write /Library/Preferences/[domain]'
        system_keylist = CFPreferencesCopyKeyList(
            BUNDLE_ID, kCFPreferencesAnyUser, kCFPreferencesCurrentHost
        )

        # CFPreferencesCopyAppValue() in get_macos_pref() will handle returning the
        # appropriate value using the search order, so merging prefs in order
        # here isn't necessary
        for keylist in [system_keylist, user_keylist]:
            if keylist:
                for key in keylist:
                    prefs[key] = self._get_macos_pref(key)
        return prefs

    def _get_file_prefs(self):
        r"""Lookup preferences for Windows in a standardized path, such as:
        * `C:\\Users\username\AppData\Local\Autopkg\config.{plist,json}`
        * `/home/username/.config/Autopkg/config.{plist,json}`
        Tries to find `config.plist`, then `config.json`."""

        config_dir = appdirs.user_config_dir(APP_NAME, appauthor=False)

        # Try a plist config, then a json config.
        data = self._parse_json_or_plist_file(os.path.join(config_dir, "config.plist"))
        if data:
            return data
        data = self._parse_json_or_plist_file(os.path.join(config_dir, "config.json"))
        if data:
            return data

        return {}

    def _set_macos_pref(self, key, value) -> None:
        """Sets a preference for domain"""
        try:
            CFPreferencesSetAppValue(key, value, BUNDLE_ID)
            if not CFPreferencesAppSynchronize(BUNDLE_ID):
                raise PreferenceError(f"Could not synchronize preference {key}")
        except Exception as err:
            raise PreferenceError(f"Could not set {key} preference: {err}") from err

    def read_file(self, file_path) -> None:
        """Read in a file and add the key/value pairs into preferences."""
        # Determine type or file: plist or json
        data = self._parse_json_or_plist_file(file_path)
        for k in data:
            self.prefs[k] = data[k]

    def _write_json_file(self) -> None:
        """Write out the prefs into JSON."""
        try:
            assert self.file_path is not None
            with open(self.file_path, "w") as f:
                json.dump(
                    self.prefs,
                    f,
                    skipkeys=True,
                    ensure_ascii=True,
                    indent=2,
                    sort_keys=True,
                )
        except Exception as e:
            log_err(f"Unable to write out JSON: {e}")

    def _write_plist_file(self) -> None:
        """Write out the prefs into a Plist."""
        try:
            assert self.file_path is not None
            with open(self.file_path, "wb") as f:
                plistlib.dump(self.prefs, f)
        except Exception as e:
            log_err(f"Unable to write out plist: {e}")

    def write_file(self) -> None:
        """Write preferences back out to file."""
        if not self.file_path:
            # Nothing to do if we weren't given a file
            return
        if self.type == "json":
            self._write_json_file()
        elif self.type == "plist":
            self._write_plist_file()

    def get_pref(self, key) -> Any | None:
        """Retrieve a preference value."""
        return deepcopy(self.prefs.get(key))

    def get_all_prefs(self) -> VarDict:
        """Retrieve a dict of all preferences."""
        return self.prefs

    def set_pref(self, key, value) -> None:
        """Set a preference value."""
        self.prefs[key] = value
        # On macOS, write it back to preferences domain if we didn't use a file
        if is_mac() and self.type is None:
            self._set_macos_pref(key, value)
        elif self.file_path is not None:
            self.write_file()
        else:
            log_err(f"WARNING: Preference change {key}=''{value}'' was not saved.")


# Set the global preferences object
globalPreferences = Preferences()

# Set the global recipe map. The four top-level dicts map:
#   identifiers           -> identifier string -> absolute recipe path
#   shortnames            -> recipe shortname  -> absolute recipe path
#   overrides             -> override shortname -> absolute override path
#   overrides-identifiers -> override identifier -> absolute override path
globalRecipeMap: dict[str, dict[str, str]] = {
    "identifiers": {},
    "shortnames": {},
    "overrides": {},
    "overrides-identifiers": {},
}


def get_pref(key) -> Any | None:
    """Return a single pref value (or None) for a domain."""
    return globalPreferences.get_pref(key)


def set_pref(key, value) -> None:
    """Sets a preference for domain"""
    globalPreferences.set_pref(key, value)


def get_all_prefs() -> VarDict:
    """Return a dict (or an empty dict) with the contents of all
    preferences in the domain."""
    return globalPreferences.get_all_prefs()


def remove_recipe_extension(name) -> str:
    """Removes supported recipe extensions from a filename or path.
    If the filename or path does not end with any known recipe extension,
    the name is returned as is."""
    for ext in RECIPE_EXTS:
        if name.endswith(ext):
            return name[: -len(ext)]
    return name


def recipe_from_file(filename) -> VarDict | None:
    """Create a recipe dictionary from a file. Handle exceptions and log.

    YAML recipes are parsed with ``yaml.safe_load`` (not ``FullLoader``).
    Recipe documents are always plain mappings of primitives, so the safe
    loader is sufficient for every legitimate recipe in the ecosystem.
    This is a deliberate defence against arbitrary-code-execution via
    crafted YAML tags (CVE-2020-14343-class issues) — doubly important
    now that the recipe map backport causes every ``.recipe.yaml`` in
    ``RECIPE_SEARCH_DIRS`` to be parsed during every map build and
    lookup, not just when the user explicitly invokes the recipe."""
    if not os.path.isfile(filename):
        return

    if filename.endswith(".yaml"):
        try:
            with open(filename, "rb") as f:
                recipe_dict = yaml.safe_load(f)
            return recipe_dict
        except Exception as err:
            log_err(f"WARNING: yaml error for {filename}: {err}")
            return

    else:
        try:
            # try to read it as a plist
            with open(filename, "rb") as f:
                recipe_dict = plistlib.load(f)
            return recipe_dict
        except Exception as err:
            log_err(f"WARNING: plist error for {filename}: {err}")
            return


def get_identifier(recipe) -> str | None:
    """Return identifier from recipe dict. Tries the Identifier
    top-level key and falls back to the legacy key location."""
    try:
        return recipe["Identifier"]
    except (KeyError, AttributeError):
        try:
            return recipe["Input"]["IDENTIFIER"]
        except (KeyError, AttributeError):
            return None
    except TypeError:
        return None


def get_identifier_from_recipe_file(filename) -> str | None:
    """Attempts to read filename and get the
    identifier. Otherwise, returns None."""
    recipe_dict = recipe_from_file(filename)
    return get_identifier(recipe_dict)


def valid_recipe_dict_with_keys(recipe_dict, keys_to_verify) -> bool:
    """Attempts to read a dict and ensures the keys in
    keys_to_verify exist. Returns False on any failure, True otherwise."""
    if recipe_dict:
        for key in keys_to_verify:
            if key not in recipe_dict:
                return False
        # if we get here, we found all the keys
        return True
    return False


def valid_recipe_dict(recipe_dict) -> bool:
    """Returns True if recipe dict is a valid recipe,
    otherwise returns False"""
    return (
        valid_recipe_dict_with_keys(recipe_dict, ["Input", "Process"])
        or valid_recipe_dict_with_keys(recipe_dict, ["Input", "Recipe"])
        or valid_recipe_dict_with_keys(recipe_dict, ["Input", "ParentRecipe"])
    )


def valid_recipe_file(filename) -> bool:
    """Returns True if filename contains a valid recipe,
    otherwise returns False"""
    recipe_dict = recipe_from_file(filename)
    return valid_recipe_dict(recipe_dict)


def valid_override_dict(recipe_dict) -> bool:
    """Returns True if the recipe is a valid override,
    otherwise returns False"""
    return valid_recipe_dict_with_keys(
        recipe_dict, ["Input", "ParentRecipe"]
    ) or valid_recipe_dict_with_keys(recipe_dict, ["Input", "Recipe"])


def valid_override_file(filename) -> bool:
    """Returns True if filename contains a valid override,
    otherwise returns False"""
    override_dict = recipe_from_file(filename)
    return valid_override_dict(override_dict)


def get_search_dirs() -> list[str]:
    """Return search dirs from preferences or default list"""
    dirs: list[str] = get_pref("RECIPE_SEARCH_DIRS")
    if isinstance(dirs, str):
        # convert a string to a list
        dirs = [dirs]
    return dirs or list(DEFAULT_SEARCH_DIRS)


def get_override_dirs() -> list[str]:
    """Return override dirs from preferences or default list"""
    default = [DEFAULT_USER_OVERRIDES_DIR]

    dirs: list[str] = get_pref("RECIPE_OVERRIDE_DIRS")
    if isinstance(dirs, str):
        # convert a string to a list
        dirs = [dirs]
    return dirs or default


def find_recipe_by_identifier_on_disk(identifier, search_dirs) -> str | None:
    """Search search_dirs on disk for a recipe with the given identifier.

    This is the legacy on-disk scan used as a fallback when the recipe map
    cannot resolve a recipe."""
    for directory in search_dirs:
        normalized_dir = os.path.abspath(os.path.expanduser(directory))
        patterns = [os.path.join(normalized_dir, f"*{ext}") for ext in RECIPE_EXTS]
        patterns.extend(
            [os.path.join(normalized_dir, f"*/*{ext}") for ext in RECIPE_EXTS]
        )
        for pattern in patterns:
            matches = glob.glob(pattern)
            for match in matches:
                if get_identifier_from_recipe_file(match) == identifier:
                    return match

    return None


def find_recipe_by_name_on_disk(name, search_dirs) -> str | None:
    """Search search_dirs on disk for a recipe by file/directory naming rules.

    This is the legacy on-disk scan used as a fallback when the recipe map
    cannot resolve a recipe."""
    # drop extension from the end of the name because we're
    # going to add it back on...
    name = remove_recipe_extension(name)
    # search by "Name", using file/directory hierarchy rules
    for directory in search_dirs:
        normalized_dir = os.path.abspath(os.path.expanduser(directory))
        patterns = [os.path.join(normalized_dir, f"{name}{ext}") for ext in RECIPE_EXTS]
        patterns.extend(
            [os.path.join(normalized_dir, f"*/{name}{ext}") for ext in RECIPE_EXTS]
        )
        for pattern in patterns:
            matches = glob.glob(pattern)
            for match in matches:
                if valid_recipe_file(match):
                    return match

    return None


# Backwards-compatible alias. The recipe-map port below keeps this name
# pointing at the on-disk scanner so existing tests that mock
# ``find_recipe_by_identifier`` keep working. Callers that want the new
# map-based behaviour should use ``find_recipe_by_identifier_in_map`` explicitly.
find_recipe_by_identifier = find_recipe_by_identifier_on_disk


# ---------------------------------------------------------------------------
# Recipe map: backport from dev-3.x
# ---------------------------------------------------------------------------
#
# The recipe map is an on-disk JSON cache of every recipe and override
# discovered on the system. It lets autopkg resolve a recipe by identifier
# or shortname without walking every recipe directory on each invocation,
# which is the dominant cost for users with many recipe repos.
#
# Glossary:
#   identifier      A recipe's globally-unique reverse-DNS ID, read from
#                   its ``Identifier`` field (e.g. ``com.github.autopkg.X``).
#   shortname       The recipe's filename minus the ``.recipe`` /
#                   ``.recipe.plist`` / ``.recipe.yaml`` extension.
#   override        A recipe in RECIPE_OVERRIDE_DIRS. Has precedence over a
#                   stock recipe of the same name during resolution.
#   search dir      An entry in RECIPE_SEARCH_DIRS.
#   pref-scoped     The persisted map reflects the prefs at build time.
#                   CLI ``--search-dir`` / ``--override-dir`` flags that
#                   differ from the pref baseline bypass the map and
#                   scan only the requested dirs on disk.
#
# On-disk layout:
#   Path:  ``~/Library/AutoPkg/recipe_map.json``
#          (overridable via AUTOPKG_RECIPE_MAP_PATH env var or
#          RECIPE_MAP_PATH pref — issue #901)
#   Keys:  ``identifiers``, ``shortnames``, ``overrides``,
#          ``overrides-identifiers``, plus ``schema_version`` for
#          forward-compat.
#
# UX divergence from dev-3.x: the original behaviour exited with an error
# when the map was missing. We auto-create it on demand instead, and
# expose an explicit ``autopkg generate-recipe-map`` verb for environments
# (e.g. CI/CD) that want to build the cache up-front. See issues #884,
# #893, #898.
#
# Resolution flow (used by ``find_recipe`` in Code/autopkg):
#   1. Did the caller supply CLI dirs that differ from prefs?
#        yes → on-disk scan of ONLY the supplied dirs
#        no  → consult globalRecipeMap (O(1))
#   2. Miss?
#        yes → on-disk fallback of the effective dirs
#   3. Still miss? ``locate_recipe`` triggers one cwd-inclusive rebuild
#      (once per process) and retries.


def find_recipe_by_identifier_in_map(
    identifier: str, skip_overrides: bool = False
) -> str | None:
    """Resolve an identifier to a recipe path via the global recipe map.

    Returns None if no entry exists or the cached path has disappeared from
    disk (stale map). We only stat the file — parsing it to confirm it's a
    valid recipe would be prohibitively expensive on the hot path (every
    shared-processor lookup calls this), and the map was built from a valid
    recipe to begin with."""
    if not skip_overrides and identifier in globalRecipeMap.get(
        "overrides-identifiers", {}
    ):
        override_path = globalRecipeMap["overrides-identifiers"][identifier]
        if os.path.isfile(override_path):
            return override_path
    if identifier in globalRecipeMap.get("identifiers", {}):
        recipe_path = globalRecipeMap["identifiers"][identifier]
        if os.path.isfile(recipe_path):
            return recipe_path
    return None


def find_recipe_by_name_in_map(name: str, skip_overrides: bool = False) -> str | None:
    """Resolve a recipe shortname to a recipe path via the global recipe map.

    Overrides take precedence over stock recipes unless ``skip_overrides`` is
    True. Returns None if no entry exists or the cached path has disappeared
    from disk. See ``find_recipe_by_identifier_in_map`` for why we don't
    re-parse the file here."""
    if not skip_overrides and name in globalRecipeMap.get("overrides", {}):
        override_path = globalRecipeMap["overrides"][name]
        if os.path.isfile(override_path):
            return override_path
    if name in globalRecipeMap.get("shortnames", {}):
        recipe_path = globalRecipeMap["shortnames"][name]
        if os.path.isfile(recipe_path):
            return recipe_path
    return None


def find_name_from_identifier(identifier: str) -> str | None:
    """Reverse lookup: return a shortname for the given identifier, or None."""
    recipe_path = globalRecipeMap.get("identifiers", {}).get(identifier)
    if recipe_path is None:
        log_err(f"Could not find shortname from {identifier}!")
        return None
    for shortname, path in globalRecipeMap.get("shortnames", {}).items():
        if recipe_path == path:
            return shortname
    log_err(f"Could not find shortname from {identifier}!")
    return None


def find_identifier_from_name(name: str) -> str | None:
    """Reverse lookup: return an identifier for the given shortname, or None."""
    recipe_path = globalRecipeMap.get("shortnames", {}).get(name)
    if recipe_path is None:
        log_err(f"Could not find identifier from {name}!")
        return None
    for recipe_id, path in globalRecipeMap.get("identifiers", {}).items():
        if recipe_path == path:
            return recipe_id
    log_err(f"Could not find identifier from {name}!")
    return None


# Keys in globalRecipeMap that index by recipe Identifier (read from the
# plist/yaml). All other keys index by shortname (filename minus extension).
_IDENTIFIER_KEYS = frozenset({"identifiers", "overrides-identifiers"})


def map_key_to_paths(keyname: str, repo_dir: str) -> dict[str, str]:
    """Walk ``repo_dir`` one level deep and emit {key: absolute_path} entries
    suitable for inclusion in ``globalRecipeMap[keyname]``.

    For identifier-keyed dicts (``identifiers``, ``overrides-identifiers``)
    the key is read from the recipe file's Identifier field; for the
    shortname-keyed dicts (``shortnames``, ``overrides``) the key is the
    filename minus the recipe extension.

    First-wins: if a key is already present in the return dict or in
    ``globalRecipeMap[keyname]`` the new path is ignored."""
    recipe_map: dict[str, str] = {}
    normalized_dir = os.path.abspath(os.path.expanduser(repo_dir))
    patterns = [os.path.join(normalized_dir, f"*{ext}") for ext in RECIPE_EXTS]
    patterns.extend([os.path.join(normalized_dir, f"*/*{ext}") for ext in RECIPE_EXTS])
    use_identifier = keyname in _IDENTIFIER_KEYS
    for pattern in patterns:
        for match in glob.glob(pattern):
            if use_identifier:
                key = get_identifier_from_recipe_file(match)
            else:
                key = remove_recipe_extension(os.path.basename(match))
            if not key:
                log_err(
                    f"WARNING: {match} is potentially an invalid file, not "
                    "adding it to the recipe map! Please file a GitHub Issue "
                    "for this repo."
                )
                continue
            if key in recipe_map or key in globalRecipeMap.get(keyname, {}):
                # first-wins; do not overwrite an existing entry
                continue
            recipe_map[key] = match
    return recipe_map


def calculate_recipe_map(
    extra_search_dirs: list[str] | None = None,
    extra_override_dirs: list[str] | None = None,
    skip_cwd: bool = True,
    persist: bool | None = None,
) -> None:
    """Recalculate ``globalRecipeMap`` from scratch by walking every recipe
    search directory and every override directory.

    Mutates ``globalRecipeMap`` in place rather than rebinding the name so
    any module that imported the symbol with ``from autopkglib import
    globalRecipeMap`` continues to see the fresh contents.

    ``persist`` controls whether the new map is written to disk:

    ===============  =======================================================
    Value            Behaviour
    ===============  =======================================================
    ``None``         Default. Persist **iff** no ``extra_*`` dirs were
                     supplied. Callers that pass transient extras don't
                     want their view leaking into the on-disk cache.
    ``True``         Always persist. Used by ``generate-recipe-map``.
    ``False``        Never persist. Used by ``locate_recipe``'s on-miss
                     rebuild, which is only expanding the in-memory view
                     for the current process.
    ===============  ====================================================="""
    # Mutate in place so every importer sees the refresh.
    for sub in (
        "identifiers",
        "shortnames",
        "overrides",
        "overrides-identifiers",
    ):
        globalRecipeMap.setdefault(sub, {}).clear()

    extra_search_dirs = list(extra_search_dirs or [])
    extra_override_dirs = list(extra_override_dirs or [])

    search_dirs = get_pref("RECIPE_SEARCH_DIRS") or list(DEFAULT_SEARCH_DIRS)
    if isinstance(search_dirs, str):
        search_dirs = [search_dirs]

    for search_dir in list(search_dirs) + extra_search_dirs:
        if search_dir == "." and skip_cwd:
            # Deliberately skip '.' — adding cwd to the persistent map is
            # surprising for users who run autopkg from arbitrary locations.
            continue
        elif search_dir == ".":
            # If the caller opted back in to scanning '.', resolve it so the
            # absolute path ends up in the map.
            search_dir = os.path.abspath(".")
        globalRecipeMap["identifiers"].update(
            map_key_to_paths("identifiers", search_dir)
        )
        globalRecipeMap["shortnames"].update(map_key_to_paths("shortnames", search_dir))

    for override in get_override_dirs() + extra_override_dirs:
        if override == ".":
            # Match the search-dir behaviour: '.' is only scanned when the
            # caller opts in via skip_cwd=False.
            if skip_cwd:
                continue
            override = os.path.abspath(".")
        globalRecipeMap["overrides"].update(map_key_to_paths("overrides", override))
        globalRecipeMap["overrides-identifiers"].update(
            map_key_to_paths("overrides-identifiers", override)
        )

    if persist is None:
        persist = not (extra_search_dirs or extra_override_dirs)
    if persist:
        write_recipe_map_to_disk()


# Schema version baked into the persisted map. Increment when the on-disk
# format changes in a non-backwards-compatible way so we can force a
# rebuild rather than reading stale or incompatible content.
RECIPE_MAP_SCHEMA_VERSION = 1


def _recipe_map_path() -> str:
    """Return the absolute, expanded path to the recipe map file on disk.

    Resolution order (issue #901):
    1. ``AUTOPKG_RECIPE_MAP_PATH`` environment variable (CI/CD friendly).
    2. ``RECIPE_MAP_PATH`` preference key (per-user override).
    3. The default location under ``autopkg_user_folder()``.

    Security notes:
    * Environment variables are honoured regardless of effective UID,
      but when running as root we log a prominent warning so operators
      noticing the deviation in their logs can investigate. Users who
      run ``sudo autopkg`` in CI pipelines should strip ``AUTOPKG_*``
      from their ``env_keep`` list to avoid letting an unprivileged
      caller influence a privileged process's write target.
    * ``DEFAULT_RECIPE_MAP`` is stored unexpanded (with a leading ``~``)
      so tests can monkey-patch ``os.path.expanduser``; resolve it
      lazily here."""
    override_source: str | None = None
    override = os.environ.get("AUTOPKG_RECIPE_MAP_PATH")
    if override:
        override_source = "AUTOPKG_RECIPE_MAP_PATH environment variable"
    else:
        pref = get_pref("RECIPE_MAP_PATH")
        if pref:
            override = pref
            override_source = "RECIPE_MAP_PATH preference"

    target = override or DEFAULT_RECIPE_MAP
    resolved = os.path.abspath(os.path.expanduser(target))

    if override and override_source:
        try:
            euid = os.geteuid()
        except AttributeError:
            # Windows doesn't have geteuid; treat as unprivileged.
            euid = -1
        if euid == 0:
            log_err(
                "SECURITY WARNING: autopkg is running as root and the "
                f"recipe map path has been redirected via {override_source} "
                f"to {resolved}. If this was not set by the system "
                "administrator it may be a privilege-escalation attempt. "
                "Consider stripping AUTOPKG_* from your sudoers env_keep "
                "configuration."
            )
        else:
            log(f"Recipe map path overridden via {override_source}: {resolved}")
    return resolved


def _recipe_map_disabled() -> bool:
    """Escape hatch. If either the ``AUTOPKG_DISABLE_RECIPE_MAP`` env var
    or the ``DISABLE_RECIPE_MAP`` pref is truthy, the recipe map is bypassed
    entirely: lookups fall back to on-disk scans and writes are skipped.

    Intended as a mitigation for users who hit a bug they can't reproduce
    locally — they can bypass the map without editing code."""
    if os.environ.get("AUTOPKG_DISABLE_RECIPE_MAP"):
        return True
    pref = get_pref("DISABLE_RECIPE_MAP")
    return bool(pref)


# Module-level latch tracking whether the last write attempt failed. When
# True we skip further writes for the life of the process to avoid spamming
# the log with the same OSError on every verb. Test fixtures reset this
# in setUp by assigning directly.
_recipe_map_write_disabled: bool = False


def write_recipe_map_to_disk() -> None:
    """Persist ``globalRecipeMap`` to the recipe-map file as sorted JSON.

    The write is atomic: we write to ``<path>.tmp`` in the same directory,
    fsync, then ``os.replace`` it into position. This protects concurrent
    autopkg invocations from reading a half-written file.

    Failures to write (permission denied, read-only filesystem, etc.) are
    logged but not raised — the in-memory map is still usable for the
    lifetime of the process. After the first failure subsequent calls in
    the same process are silent no-ops to avoid log spam."""
    global _recipe_map_write_disabled
    if _recipe_map_write_disabled:
        return
    if _recipe_map_disabled():
        # Escape hatch: don't touch disk at all.
        return

    target = _recipe_map_path()
    # Ensure the containing directory exists. autopkg_user_folder() handles
    # the default location; if the user pointed RECIPE_MAP_PATH at a
    # custom spot we need to ensure its directory is present too.
    autopkg_user_folder()
    target_dir = os.path.dirname(target)
    if target_dir:
        try:
            os.makedirs(target_dir, exist_ok=True)
        except OSError:
            # Fall through; the open below will surface the real error.
            pass

    # Wrap the persisted dict with a schema version so future versions can
    # detect and migrate/rebuild incompatible formats.
    payload = {
        "schema_version": RECIPE_MAP_SCHEMA_VERSION,
        **globalRecipeMap,
    }

    # Create the tempfile via tempfile.mkstemp so we get O_EXCL semantics
    # and explicit mode bits. This prevents a classic symlink-TOCTOU
    # attack (CWE-59/CWE-377): if another principal can pre-create a
    # symlink at ``<target>.tmp`` pointing at an attacker-chosen file,
    # a plain ``open(tmp, "w")`` would follow the symlink and truncate
    # the target. mkstemp refuses to follow existing symlinks.
    tmp_dir = target_dir or "."
    tmp_basename = f".{os.path.basename(target)}.tmp"
    tmp_fd = -1
    tmp: str | None = None
    try:
        import tempfile as _tempfile

        tmp_fd, tmp = _tempfile.mkstemp(
            prefix=tmp_basename,
            dir=tmp_dir,
        )
        # Tighten permissions so a shared-homedir setup doesn't leak the
        # map's file listing to other users on the system.
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            # Chmod not supported on every filesystem; soft-fail.
            pass
        with os.fdopen(tmp_fd, "w") as f:
            # fdopen takes ownership of the fd; null it out so the
            # finally clause below doesn't double-close.
            tmp_fd = -1
            json.dump(
                payload,
                f,
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            )
            f.flush()
            try:
                os.fsync(f.fileno())
            except (OSError, AttributeError):
                # fsync can fail on some filesystems (e.g., tmpfs). The
                # replace below is still atomic enough for our needs.
                pass
        os.replace(tmp, target)
        tmp = None  # Successfully renamed; no cleanup needed.
    except OSError as err:
        _recipe_map_write_disabled = True
        log_err(
            f"WARNING: Could not write recipe map to {target}: {err}. "
            "Further write attempts in this process will be skipped. "
            "To resolve: check write permissions on the target, set "
            "RECIPE_MAP_PATH (or AUTOPKG_RECIPE_MAP_PATH) to a writable "
            "location, or set AUTOPKG_DISABLE_RECIPE_MAP=1 to bypass "
            "the cache entirely."
        )
    finally:
        # Best-effort cleanup of the partial tempfile if we didn't rename
        # it into position.
        if tmp_fd != -1:
            try:
                os.close(tmp_fd)
            except OSError:
                pass
        if tmp and os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


def handle_reading_recipe_map_file() -> dict:
    """Read the recipe map from disk. Returns an empty dict on any I/O or
    JSON error — callers are expected to treat that as a signal to rebuild
    the map."""
    try:
        with open(_recipe_map_path()) as f:
            return json.load(f)
    except FileNotFoundError:
        # Silent: this is the normal case on a fresh install and the caller
        # will trigger a rebuild.
        return {}
    except (OSError, json.JSONDecodeError) as err:
        log_err(f"WARNING: Cannot read the recipe map file: {err}")
        return {}


# Required top-level keys in the in-memory / persisted map structure.
_EXPECTED_MAP_KEYS = frozenset(
    ("identifiers", "shortnames", "overrides", "overrides-identifiers")
)


def validate_recipe_map(recipe_map: dict) -> bool:
    """Return True if ``recipe_map`` has the full set of expected top-level
    keys AND, if a ``schema_version`` is present, it matches what this
    version of autopkg knows how to read.

    Missing ``schema_version`` is treated as valid for forward-compat with
    older persisted files that pre-date the version field; missing required
    dict keys always invalidate the map."""
    if not _EXPECTED_MAP_KEYS.issubset(recipe_map.keys()):
        return False
    version = recipe_map.get("schema_version")
    if version is None:
        # Legacy file from a version before we started writing the
        # schema_version key — treat as v1.
        return True
    return version == RECIPE_MAP_SCHEMA_VERSION


def read_recipe_map(rebuild: bool = False, allow_continuing: bool = False) -> None:
    """Load the recipe map from disk into ``globalRecipeMap``.

    * ``rebuild=True`` forces a full rebuild regardless of on-disk state.
    * Otherwise: valid file → load; missing/invalid → auto-rebuild once.

    Dev-3.x printed an error and called ``sys.exit(1)`` when the map was
    missing. We auto-rebuild silently instead — fresh installs and CI
    pipelines hit that case constantly. See issues #884, #893, #898.

    ``allow_continuing`` is retained for API compatibility with dev-3.x
    callers that used it to signal "the map may not exist yet". The new
    auto-create behaviour makes it a no-op."""
    _ = allow_continuing  # retained for API compatibility

    if _recipe_map_disabled():
        return

    if rebuild:
        calculate_recipe_map()
        return

    recipe_map = handle_reading_recipe_map_file()
    if validate_recipe_map(recipe_map):
        for sub in _EXPECTED_MAP_KEYS:
            globalRecipeMap.setdefault(sub, {}).clear()
            globalRecipeMap[sub].update(recipe_map.get(sub, {}))
        return

    if not recipe_map:
        log(
            "Recipe map not found; generating it on demand. Run "
            "`autopkg generate-recipe-map` explicitly (e.g. in CI) to "
            "avoid paying this cost on every fresh run."
        )
    else:
        log("Recipe map is invalid or from an older schema; rebuilding now.")
    calculate_recipe_map()


def get_autopkg_version() -> str:
    """Gets the version number of autopkg"""
    try:
        version_file = importlib.resources.files(__name__).joinpath("version.plist")
        with version_file.open("rb") as f:
            version_plist = plistlib.load(f)
    except Exception as ex:
        log_err(f"Unable to get autopkg version: {ex}")
        return "UNKNOWN"
    try:
        return version_plist["Version"]
    except (AttributeError, TypeError):
        return "UNKNOWN"


def version_equal_or_greater(this, that) -> bool:
    """Compares two LooseVersion objects. Returns True if this is
    equal to or greater than that"""
    return LooseVersion(this) >= LooseVersion(that)


def update_data(a_dict, key, value) -> None:
    """Update a_dict keys with value. Existing data can be referenced
    by wrapping the key in %percent% signs."""

    def getdata(match) -> Any:
        """Returns data from a match object"""
        return a_dict[match.group("key")]

    def do_variable_substitution(item) -> Any:
        """Do variable substitution for item"""
        if isinstance(item, str):
            try:
                item = RE_KEYREF.sub(getdata, item)
            except KeyError as err:
                log_err(f"Use of undefined key in variable substitution: {err}")
        elif isinstance(item, (list, NSArray)):
            for index in range(len(item)):
                item[index] = do_variable_substitution(item[index])
        elif isinstance(item, (dict, NSDictionary)):
            # Modify a copy of the original
            if isinstance(item, dict):
                item_copy = item.copy()
            else:
                # Need to specify the copy is mutable for NSDictionary
                item_copy = item.mutableCopy()
            for key, value in list(item.items()):
                item_copy[key] = do_variable_substitution(value)
            return item_copy
        return item

    a_dict[key] = do_variable_substitution(value)


def is_executable(exe_path) -> bool:
    """Is exe_path executable?"""
    return os.path.exists(exe_path) and os.access(exe_path, os.X_OK)


def find_binary(binary: str, env: dict | None = None) -> str | None:
    r"""Returns the full path for `binary`, or `None` if it was not found.

    The search order is as follows:
    * A key in the optional `env` dictionary named `<binary>_PATH`.
        Where `binary` is uppercase. E.g., `git` -> `GIT`.
    * A preference named `<binary>_PATH` uppercase, as above.
    * The directories listed in the system-dependent `$PATH` environment variable.
    * On POSIX-y platforms only: `/usr/bin/<binary>`
    In all cases, the binary found at any path must be executable to be used.

    The `binary` parameter should be given without any file extension. A platform
    specific file extension for executables will be added automatically, as needed.

    Example: `find_binary('curl')` may return `C:\Windows\system32\curl.exe`.
    """

    if env is None:
        env = {}
    pref_key = f"{binary.upper()}_PATH"

    bin_env = env.get(pref_key)
    if bin_env:
        if not is_executable(bin_env):
            log_err(
                f"WARNING: path given in the '{pref_key}' environment: '{bin_env}' "
                "either doesn't exist or is not executable! "
                f"Continuing search for usable '{binary}'."
            )
        else:
            return env[pref_key]

    bin_pref = get_pref(pref_key)
    if bin_pref:
        if not is_executable(bin_pref):
            log_err(
                f"WARNING: path given in the '{pref_key}' preference: '{bin_pref}' "
                "either doesn't exist or is not executable! "
                f"Continuing search for usable '{binary}'."
            )
        else:
            return bin_pref

    if is_windows():
        extension = ".exe"
    else:
        extension = ""

    full_binary = f"{binary}{extension}"

    for search_dir in os.get_exec_path():
        exe_path = os.path.join(search_dir, full_binary)
        if is_executable(exe_path):
            return exe_path

    if (is_linux() or is_mac()) and is_executable(f"/usr/bin/{binary}"):
        return f"/usr/bin/{binary}"

    log_err(
        f"WARNING: Unable to find '{full_binary}' in either configured, "
        "or environmental locations. Things aren't guaranteed to work from here."
    )
    return None


# Processor and ProcessorError base class definitions


class ProcessorError(Exception):
    """Base Error class"""

    pass


class Processor:
    """Processor base class.

    Processors accept a property list as input, process its contents, and
    returns a new or updated property list that can be processed further.
    """

    lifecycle: dict = {}

    def __init__(self, env=None, infile=None, outfile=None):
        # super(Processor, self).__init__()
        self.env = env
        if infile is None:
            self.infile = sys.stdin
        else:
            self.infile = infile
        if outfile is None:
            self.outfile = sys.stdout
        else:
            self.outfile = outfile

    def output(self, msg, verbose_level=1) -> None:
        """Print a message if verbosity is >= verbose_level"""
        if int(self.env.get("verbose", 0)) >= verbose_level:
            print(f"{self.__class__.__name__}: {msg}")

    def main(self) -> None:
        """Stub method"""
        raise ProcessorError("Abstract method main() not implemented.")

    def get_manifest(self) -> tuple[str, VarDict, VarDict]:
        """Return Processor's description, input and output variables"""
        try:
            return (self.description, self.input_variables, self.output_variables)
        except AttributeError as err:
            raise ProcessorError(f"Missing manifest: {err}") from err

    def read_input_plist(self) -> None:
        """Read environment from input plist."""

        try:
            indata = self.infile.buffer.read()
            if indata:
                self.env = plistlib.loads(indata)
            else:
                self.env = {}
        except BaseException as err:
            raise ProcessorError(err) from err

    def write_output_plist(self) -> None:
        """Write environment to output as plist."""

        if self.env is None:
            return

        plist_safe = {}

        for env_key in self.env:
            if self.env[env_key] is not None:
                plist_safe[env_key] = self.env[env_key]

        try:
            with open(self.outfile, "wb") as f:
                plistlib.dump(plist_safe, f)
        except TypeError:
            plistlib.dump(plist_safe, self.outfile.buffer)
        except BaseException as err:
            raise ProcessorError(err) from err

    def parse_arguments(self) -> None:
        """Parse arguments as key='value'."""

        if self.env is None:
            self.env = {}

        for arg in sys.argv[1:]:
            key, sep, value = arg.partition("=")
            if sep != "=":
                raise ProcessorError(f"Illegal argument '{arg}'")
            update_data(self.env, key, value)

    def inject(self, arguments) -> None:
        """Update environment data with arguments."""
        for key, value in list(arguments.items()):
            update_data(self.env, key, value)

    def process(self) -> None:
        """Main processing loop."""
        # Check if this processor is deprecated and emit warning
        deprecated_version = self.lifecycle.get("deprecated")
        if deprecated_version:
            self.show_deprecation(self.get_deprecation_warning(deprecated_version))

        # Make sure all required arguments have been supplied.
        for variable, flags in list(self.input_variables.items()):
            # Apply default values to unspecified input variables
            if "default" in list(flags.keys()) and (variable not in self.env):
                self.env[variable] = flags["default"]
                self.output(
                    f"No value supplied for {variable}, setting default value "
                    f"of: {self.env[variable]}",
                    verbose_level=2,
                )
            # Make sure all required arguments have been supplied.
            if flags.get("required") and (variable not in self.env):
                raise ProcessorError(f"{self.__class__.__name__} requires {variable}")

        self.main()
        return self.env

    def cmdexec(self, command, description) -> str | None:
        """Execute a command and return output."""

        try:
            proc = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = proc.communicate()
        except OSError as err:
            raise ProcessorError(
                f"{command[0]} execution failed with error code "
                f"{err.errno}: {err.strerror}"
            ) from err
        if proc.returncode != 0:
            raise ProcessorError(f"{description} failed: {stderr}")

        return stdout

    def execute_shell(self) -> None:
        """Execute as a standalone binary on the commandline."""

        try:
            if not sys.argv[1:]:
                self.read_input_plist()
            else:
                self.parse_arguments()
            self.process()
            self.write_output_plist()
        except ProcessorError as err:
            log_err(f"ProcessorError: {err}")
            sys.exit(10)
        else:
            sys.exit(0)

    def load_plist_from_file(
        self,
        plist_file: FileOrPath,
        exception_text: str = "Unable to load plist",
    ) -> VarDict:
        """Load plist from a path or file-like object and return content as dictionary.

        If there is an error loading the file, the exception raised will be prefixed
        with `exception_text`.
        """
        fh: IO | None = None
        try:
            if isinstance(plist_file, (str, bytes, int)):
                fh = open(plist_file, "rb")
            else:
                fh = plist_file
            return plistlib.load(fh)
        except Exception as err:
            raise ProcessorError(f"{exception_text}: {err}") from err
        finally:
            if fh and isinstance(plist_file, (str, bytes, int)):
                fh.close()

    def get_deprecation_warning(self, deprecated_version: str) -> str:
        """Generate a standardized deprecation warning message.

        Args:
            deprecated_version: The AutoPkg version in which this processor was deprecated, if applicable.

        Returns:
            A formatted deprecation warning message.
        """
        return (
            f"{self.__class__.__name__} was deprecated in AutoPkg "
            f"version {deprecated_version} and may be removed in a "
            f"future release."
        )

    def show_deprecation(self, message: str) -> None:
        """Emit a deprecation warning, either from a deprecated recipe that calls
        the DeprecationWarning processor, or from a deprecated processor that calls
        this method directly.

        This both prints the warning to stdout and adds the deprecation to the
        summary results from the autopkg run.
        """
        self.output(f"WARNING: {message}")
        recipe_name = os.path.basename(self.env["RECIPE_PATH"])
        recipe_name = remove_recipe_extension(recipe_name)
        depr_summary_result = {
            "summary_text": "The following recipes have deprecation warnings:",
            "report_fields": ["name", "warning"],
            "data": {"name": recipe_name, "warning": message},
        }
        if self.output_variables:
            self.output_variables["deprecation_summary_result"] = depr_summary_result
        else:
            self.output_variables = {"deprecation_summary_result": depr_summary_result}
        self.env["deprecation_summary_result"] = depr_summary_result


# AutoPackager class definition


class AutoPackagerError(Exception):
    """Error class"""

    pass


class AutoPackagerLoadError(Exception):
    """Represent an exception loading a recipe or processor."""

    pass


class AutoPackager:
    """Instantiate and execute processors from a recipe."""

    def __init__(self, options, env):
        self.verbose = options.verbose
        self.env = env
        self.results = []
        self.env["AUTOPKG_VERSION"] = get_autopkg_version()

    def output(self, msg, verbose_level=1) -> None:
        """Print msg if verbosity is >= than verbose_level"""
        if self.verbose >= verbose_level:
            print(msg)

    def get_recipe_identifier(self, recipe) -> str | None:
        """Return the identifier given an input recipe dict."""
        identifier = recipe.get("Identifier") or recipe["Input"].get("IDENTIFIER")
        if not identifier:
            log_err("ID NOT FOUND")
            # build a pseudo-identifier based on the recipe pathname
            recipe_path = self.env.get("RECIPE_PATH")
            # get rid of filename extension
            recipe_path = remove_recipe_extension(recipe_path)
            path_parts = recipe_path.split("/")
            identifier = "-".join(path_parts)
        return identifier

    def process_cli_overrides(self, recipe, cli_values) -> None:
        """Override env with input values from the CLI:
        Start with items in recipe's 'Input' dict, merge and
        overwrite any key-value pairs appended to the
        autopkg command invocation, of the form: NAME=value
        """

        # Set up empty container for final output
        inputs = {}
        inputs.update(recipe["Input"])
        inputs.update(cli_values)
        self.env.update(inputs)
        # do any internal string substitutions
        for key, value in list(self.env.items()):
            update_data(self.env, key, value)

    def verify(self, recipe) -> None:
        """Verify a recipe and check for errors."""

        # Check for MinimumAutopkgVersion
        if "MinimumVersion" in list(recipe.keys()):
            if not version_equal_or_greater(
                self.env["AUTOPKG_VERSION"], recipe.get("MinimumVersion")
            ):
                raise AutoPackagerError(
                    "Recipe (or a parent recipe) requires at least autopkg "
                    f"version {recipe.get('MinimumVersion')}, but we are autopkg "
                    f"version {self.env['AUTOPKG_VERSION']}."
                )

        # Initialize variable set with input variables.
        variables = set(recipe["Input"].keys())
        # Add environment.
        variables.update(set(self.env.keys()))
        # Check each step of the process.
        for step in recipe["Process"]:
            try:
                processor_class = get_processor(
                    step["Processor"], verbose=self.verbose, recipe=recipe, env=self.env
                )
            except (KeyError, AttributeError) as err:
                msg = f"Unknown processor '{step['Processor']}'."
                if "SharedProcessorRepoURL" in step:
                    msg += (
                        " This shared processor can be added via the "
                        f"repo: {step['SharedProcessorRepoURL']}."
                    )
                raise AutoPackagerError(msg) from err
            except AutoPackagerLoadError as err:
                msg = (
                    f"Unable to import '{step['Processor']}', likely due "
                    "to syntax or Python error."
                )
                raise AutoPackagerError(msg) from err
            # Add arguments to set of variables.
            variables.update(set(step.get("Arguments", {}).keys()))
            # Make sure all required input variables exist.
            for key, flags in list(processor_class.input_variables.items()):
                if flags["required"] and (key not in variables):
                    raise AutoPackagerError(
                        f"{step['Processor']} requires missing argument {key}"
                    )

            # Add output variables to set.
            variables.update(set(processor_class.output_variables.keys()))

    def process(self, recipe) -> None:
        """Process a recipe."""
        identifier = self.get_recipe_identifier(recipe)
        # define a cache/work directory for use by the recipe
        cache_dir = self.env.get("CACHE_DIR") or os.path.expanduser(
            "~/Library/AutoPkg/Cache"
        )
        self.env["RECIPE_CACHE_DIR"] = os.path.join(cache_dir, identifier)

        recipe_input_dict = {}
        for key in list(self.env.keys()):
            recipe_input_dict[key] = self.env[key]
        self.results.append({"Recipe input": recipe_input_dict})

        # make sure the RECIPE_CACHE_DIR exists, creating it if needed
        if not os.path.exists(self.env["RECIPE_CACHE_DIR"]):
            try:
                os.makedirs(self.env["RECIPE_CACHE_DIR"])
            except OSError as err:
                raise AutoPackagerError(
                    f"Could not create RECIPE_CACHE_DIR {self.env['RECIPE_CACHE_DIR']}:"
                    f" {err}"
                ) from err

        if self.verbose > 2:
            pprint.pprint(self.env)

        for step in recipe["Process"]:
            if self.verbose:
                print(step["Processor"])

            processor_name = extract_processor_name_with_recipe_identifier(
                step["Processor"]
            )[0]
            processor_class = get_processor(processor_name, verbose=self.verbose)
            processor = processor_class(self.env)
            processor.inject(step.get("Arguments", {}))

            input_dict = {}
            for key in list(processor.input_variables.keys()):
                if key in processor.env:
                    input_dict[key] = processor.env[key]

            if self.verbose > 1:
                # pretty print any defined input variables
                pprint.pprint({"Input": input_dict})

            try:
                self.env = processor.process()
            except Exception as err:
                if self.verbose > 2:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    traceback.print_exc(file=sys.stdout)
                    traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
                # Well-behaved processors should handle exceptions and
                # raise ProcessorError. However, we catch Exception
                # here to ensure that unexpected/unhandled exceptions
                # from one processor do not prevent execution of
                # subsequent recipes.
                log_err(err)
                raise AutoPackagerError(
                    f"Error in {identifier}: Processor: {step['Processor']}: "
                    f"Error: {err}"
                ) from err

            output_dict = {}
            for key in list(processor.output_variables.keys()):
                # Safety workaround for Processors that may output
                # differently-named output variables than are given in
                # their output_variables
                # TODO: develop a generic solution for processors that
                #       can dynamically set their output_variables
                if processor.env.get(key):
                    output_dict[key] = self.env[key]
            if self.verbose > 1:
                # pretty print output variables
                pprint.pprint({"Output": output_dict})

            self.results.append(
                {
                    "Processor": step["Processor"],
                    "Input": input_dict,
                    "Output": output_dict,
                }
            )

            if self.env.get("stop_processing_recipe"):
                # processing should stop now
                break

        if self.verbose > 2:
            pprint.pprint(self.env)


def _cmp(x, y) -> int:
    """
    Replacement for built-in function cmp that was removed in Python 3
    Compare the two objects x and y and return an integer according to
    the outcome. The return value is negative if x < y, zero if x == y
    and strictly positive if x > y.
    """
    return (x > y) - (x < y)


class APLooseVersion(LooseVersion):
    """Subclass of distutils.version.LooseVersion to fix issues under Python 3"""

    def _pad(self, version_list, max_length) -> list:
        """Pad a version list by adding extra 0 components to the end if needed."""
        # copy the version_list so we don't modify it
        cmp_list = list(version_list)
        while len(cmp_list) < max_length:
            cmp_list.append(0)
        return cmp_list

    def _compare(self, other) -> int:
        """Complete comparison mechanism since LooseVersion's is broken in Python 3."""
        if not isinstance(other, (LooseVersion, APLooseVersion)):
            other = APLooseVersion(other)
        max_length = max(len(self.version), len(other.version))
        self_cmp_version = self._pad(self.version, max_length)
        other_cmp_version = self._pad(other.version, max_length)
        cmp_result = 0
        for index, value in enumerate(self_cmp_version):
            try:
                cmp_result = _cmp(value, other_cmp_version[index])
            except TypeError:
                # integer is less than character/string
                if isinstance(value, int):
                    return -1
                return 1
            else:
                if cmp_result:
                    return cmp_result
        return cmp_result

    def __hash__(self) -> int:
        """Hash method."""
        return hash(self.version)

    def __eq__(self, other) -> bool:
        """Equals comparison."""
        return self._compare(other) == 0

    def __ne__(self, other) -> bool:
        """Not-equals comparison."""
        return self._compare(other) != 0

    def __lt__(self, other) -> bool:
        """Less than comparison."""
        return self._compare(other) < 0

    def __le__(self, other) -> bool:
        """Less than or equals comparison."""
        return self._compare(other) <= 0

    def __gt__(self, other) -> bool:
        """Greater than comparison."""
        return self._compare(other) > 0

    def __ge__(self, other) -> bool:
        """Greater than or equals comparison."""
        return self._compare(other) >= 0


_CORE_PROCESSOR_NAMES = []
_PROCESSOR_NAMES = []


def import_processors() -> None:
    processor_files: list[str] = [
        os.path.splitext(resource.name)[0]
        for resource in importlib.resources.files(__name__).iterdir()
        if resource.name.endswith(".py")
    ]

    # Warning! Fancy dynamic importing ahead!
    #
    # import the filename as a submodule
    # then add the attribute with the same name to the globals()
    #
    # This is the equivalent of:
    #
    #    from Bar.Foo import Foo
    #
    for name in filter(lambda f: f not in ("__init__", "xattr"), processor_files):
        globals()[name] = getattr(
            __import__(__name__ + "." + name, fromlist=[name]), name
        )
        _PROCESSOR_NAMES.append(name)
        _CORE_PROCESSOR_NAMES.append(name)


# convenience functions for adding and accessing processors
# since these can change dynamically
def add_processor(name, processor_object) -> None:
    """Adds a Processor to the autopkglib namespace"""
    globals()[name] = processor_object
    if name not in _PROCESSOR_NAMES:
        _PROCESSOR_NAMES.append(name)


def extract_processor_name_with_recipe_identifier(
    processor_name,
) -> tuple[str, str | None]:
    """Returns a tuple of (processor_name, identifier), given a Processor
    name.  This is to handle a processor name that may include a recipe
    identifier, in the format:

    com.github.autopkg.recipes.somerecipe/ProcessorName

    identifier will be None if one was not extracted."""
    identifier, delim, processor_name = processor_name.partition("/")
    if not delim:
        # if no '/' was found, the first item in the tuple will be the
        # full string, the processor name
        processor_name = identifier
        identifier = None
    return (processor_name, identifier)


def get_processor(processor_name, verbose=None, recipe=None, env=None):
    """Returns a Processor object given a name and optionally a recipe,
    importing a processor from the recipe directory if available"""
    if env is None:
        env = {}
    if recipe:
        recipe_dir = os.path.dirname(recipe["RECIPE_PATH"])
        processor_search_dirs = [recipe_dir]

        # check if our processor_name includes a recipe identifier that
        # should be used to locate the recipe.
        # if so, search for the recipe by identifier in order to add
        # its dirname to the processor search dirs
        (
            processor_name,
            processor_recipe_id,
        ) = extract_processor_name_with_recipe_identifier(processor_name)
        if processor_recipe_id:
            # Prefer the recipe map (cheap, O(1) lookup); fall back to an
            # on-disk scan when the map doesn't know about this identifier.
            shared_processor_recipe_path = find_recipe_by_identifier_in_map(
                processor_recipe_id
            )
            if shared_processor_recipe_path is None:
                shared_processor_recipe_path = find_recipe_by_identifier_on_disk(
                    processor_recipe_id, env["RECIPE_SEARCH_DIRS"]
                )
            # Re-validate the map-returned path is actually a recipe before
            # adding its directory to the Python import path below. The map
            # lookup only stat's the file (for speed); this call site feeds
            # `spec.loader.exec_module`, so we want a structural check here
            # even when it costs a parse. An attacker who can write to
            # recipe_map.json cannot point us at an arbitrary directory
            # just by having a file there — the file must parse as a recipe.
            if shared_processor_recipe_path and not valid_recipe_file(
                shared_processor_recipe_path
            ):
                shared_processor_recipe_path = None
            if shared_processor_recipe_path:
                processor_search_dirs.append(
                    os.path.dirname(shared_processor_recipe_path)
                )

        # search recipe dirs for processor
        if recipe.get("PARENT_RECIPES"):
            # also look in the directories containing the parent recipes
            parent_recipe_dirs = list(
                {os.path.dirname(item) for item in recipe["PARENT_RECIPES"]}
            )
            processor_search_dirs.extend(parent_recipe_dirs)

        # Dedupe the list first
        deduped_processors = {dir for dir in processor_search_dirs}
        for directory in deduped_processors:
            processor_filename = os.path.join(directory, processor_name + ".py")
            if os.path.exists(processor_filename):
                try:
                    # attempt to import the module
                    spec = importlib.util.spec_from_file_location(
                        processor_name, processor_filename
                    )
                    _tmp = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(_tmp)
                    # look for an attribute with the step Processor name
                    _processor = getattr(_tmp, processor_name)
                    # add the processor to autopkglib's namespace
                    add_processor(processor_name, _processor)
                    # we've added a Processor, so stop searching
                    break
                except (ImportError, AttributeError) as err:
                    # if we aren't successful, that might be OK, we're
                    # going see if the processor was already imported
                    log_err(f"WARNING: {processor_filename}: {err}")
                    if verbose > 2:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        traceback.print_exc(file=sys.stdout)
                        traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
                    raise AutoPackagerLoadError(err) from err

    return globals()[processor_name]


def processor_names():
    """Return our Processor names"""
    return _PROCESSOR_NAMES


def core_processor_names():
    """Returns the names of the 'core' processors"""
    return _CORE_PROCESSOR_NAMES


def plist_serializer(obj) -> Any:
    """Serialize an object to ensure it can be dumped in plist format.

    Args:
        obj (dict, list): Object is assumed to be either a dict or list
            that will be parsed.

    Returns:
        (any): The received object will be returned, modified if required.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = "" if v is None else plist_serializer(v)
    elif isinstance(obj, list):
        for item in range(len(obj)):
            plist_serializer(obj[item])
    return obj


# when importing autopkglib, need to also import all the processors
# in this same directory


import_processors()
