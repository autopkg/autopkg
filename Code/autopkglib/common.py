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

"""Common functions and constants used by autopkglib modules."""

import hashlib
import os.path
import plistlib
import re
import sys
from distutils.version import LooseVersion
from typing import IO, Any, Dict, Union

import pkg_resources

APP_NAME = "Autopkg"
BUNDLE_ID = "com.github.autopkg"
DEFAULT_USER_LIBRARY_DIR = "~/Library/AutoPkg"
DEFAULT_LIBRARY_DIR = "/Library/AutoPkg"
DEFAULT_USER_OVERRIDES_DIR = os.path.expanduser(
    os.path.join(DEFAULT_USER_LIBRARY_DIR, "RecipeOverrides")
)
DEFAULT_USER_RECIPES_DIR = os.path.expanduser(
    os.path.join(DEFAULT_USER_LIBRARY_DIR, "Recipes")
)
DEFAULT_USER_CACHE_DIR = os.path.expanduser(
    os.path.join(DEFAULT_USER_LIBRARY_DIR, "Cache")
)
DEFAULT_USER_REPOS_DIR = os.path.expanduser(
    os.path.join(DEFAULT_USER_LIBRARY_DIR, "RecipeRepos")
)
DEFAULT_RECIPE_MAP = os.path.expanduser(
    os.path.join(DEFAULT_USER_LIBRARY_DIR, "recipe_map.json")
)
DEFAULT_GH_TOKEN = os.path.expanduser(
    os.path.join(DEFAULT_USER_LIBRARY_DIR, "gh_token")
)
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


def _cmp(x, y):
    """
    Replacement for built-in function cmp that was removed in Python 3
    Compare the two objects x and y and return an integer according to
    the outcome. The return value is negative if x < y, zero if x == y
    and strictly positive if x > y.
    """
    return (x > y) - (x < y)


class APLooseVersion(LooseVersion):
    """Subclass of distutils.version.LooseVersion to fix issues under Python 3"""

    def _pad(self, version_list, max_length):
        """Pad a version list by adding extra 0 components to the end if needed."""
        # copy the version_list so we don't modify it
        cmp_list = list(version_list)
        while len(cmp_list) < max_length:
            cmp_list.append(0)
        return cmp_list

    def _compare(self, other):
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

    def __hash__(self):
        """Hash method."""
        return hash(self.version)

    def __eq__(self, other):
        """Equals comparison."""
        return self._compare(other) == 0

    def __ne__(self, other):
        """Not-equals comparison."""
        return self._compare(other) != 0

    def __lt__(self, other):
        """Less than comparison."""
        return self._compare(other) < 0

    def __le__(self, other):
        """Less than or equals comparison."""
        return self._compare(other) <= 0

    def __gt__(self, other):
        """Greater than comparison."""
        return self._compare(other) > 0

    def __ge__(self, other):
        """Greater than or equals comparison."""
        return self._compare(other) >= 0


def version_equal_or_greater(this: LooseVersion, that: LooseVersion) -> bool:
    """Compares two LooseVersion objects. Returns True if this is
    equal to or greater than that"""
    return LooseVersion(this) >= LooseVersion(that)


def get_autopkg_version() -> str:
    """Gets the version number of autopkg"""
    try:
        version_plist = plistlib.load(
            pkg_resources.resource_stream(__name__, "version.plist")
        )
    except Exception as ex:
        log_err(f"Unable to get autopkg version: {ex}")
        return "UNKNOWN"
    try:
        return version_plist["Version"]
    except (AttributeError, TypeError):
        return "UNKNOWN"


def get_sha256_hash(filepath: str) -> str:
    """Generate a sha256 hash for the file at filepath"""
    hashfunction = hashlib.sha256()
    fileref = open(filepath, "rb")
    while 1:
        chunk = fileref.read(2**16)
        if not chunk:
            break
        hashfunction.update(chunk)
    fileref.close()
    return hashfunction.hexdigest()


def is_executable(exe_path):
    """Is exe_path executable?"""
    return os.path.exists(exe_path) and os.access(exe_path, os.X_OK)
