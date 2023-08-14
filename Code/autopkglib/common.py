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

import os.path
import re
import sys
from typing import IO, Any, Dict, Union


APP_NAME = "Autopkg"
BUNDLE_ID = "com.github.autopkg"
DEFAULT_USER_LIBRARY_DIR = "~/Library/AutoPkg"
DEFAULT_LIBRARY_DIR = "/Library/AutoPkg"
DEFAULT_USER_OVERRIDES_DIR = os.path.expanduser(os.path.join(DEFAULT_USER_LIBRARY_DIR, "RecipeOverrides"))
DEFAULT_USER_RECIPES_DIR = os.path.expanduser(os.path.join(DEFAULT_USER_LIBRARY_DIR, "Recipes"))
DEFAULT_USER_CACHE_DIR = os.path.expanduser(os.path.join(DEFAULT_USER_LIBRARY_DIR, "Cache"))
DEFAULT_USER_REPOS_DIR = os.path.expanduser(os.path.join(DEFAULT_USER_LIBRARY_DIR, "RecipeRepos"))
DEFAULT_RECIPE_MAP = os.path.expanduser(os.path.join(DEFAULT_USER_LIBRARY_DIR, "recipe_map.json"))
DEFAULT_GH_TOKEN = os.path.expanduser(os.path.join(DEFAULT_USER_LIBRARY_DIR, "gh_token"))
DEFAULT_SEARCH_DIRS = [".", DEFAULT_USER_LIBRARY_DIR, DEFAULT_LIBRARY_DIR]

RE_KEYREF = re.compile(r"%(?P<key>[a-zA-Z_][a-zA-Z_0-9]*)%")

# Supported recipe extensions
RECIPE_EXTS = (".recipe", ".recipe.plist", ".recipe.yaml")

# Type for methods that accept either a filesystem path or a file-like object.
FileOrPath = Union[IO, str, bytes, int]

# Type for ubiquitous dictionary type used throughout autopkg.
# Most commonly for `input_variables` and friends. It also applies to virtually all
# usages of plistlib results as well.
VarDict = Dict[str, Any]


def is_mac():
    """Return True if current OS is macOS."""
    return "darwin" in sys.platform.lower()


def is_windows():
    """Return True if current OS is Windows."""
    return "win32" in sys.platform.lower()


def is_linux():
    """Return True if current OS is Linux."""
    return "linux" in sys.platform.lower()


def log(msg, error=False):
    """Message logger, prints to stdout/stderr."""
    if error:
        print(msg, file=sys.stderr)
    else:
        print(msg)


def log_err(msg):
    """Message logger for errors."""
    log(msg, error=True)


def autopkg_user_folder() -> str:
    """Return a path string for the AutoPkg user folder"""
    return os.path.abspath(os.path.expanduser(DEFAULT_USER_LIBRARY_DIR))
