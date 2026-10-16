"""Supplies the package version to setuptools; everything else is in pyproject.toml.

Code/autopkglib/version.plist stays the single source of truth because
Scripts/make_new_release.py and autopkglib.get_autopkg_version() read it.
"""

import plistlib

from setuptools import setup

with open("Code/autopkglib/version.plist", "rb") as f:
    setup(version=plistlib.load(f)["Version"])
