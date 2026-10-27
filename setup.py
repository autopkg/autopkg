"""setuptools hooks that pyproject.toml can't express.

- version: read from Code/autopkglib/version.plist, the single source of
  truth that Scripts/make_new_release.py and get_autopkg_version() use.
- build_py: copy the Code/autopkg CLI script into the autopkgcmd package so
  autopkgcmd.entrypoint can run it from an installed wheel.
"""

import os
import plistlib

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildPyWithCLI(build_py):
    def run(self):
        super().run()
        if self.editable_mode:
            # entrypoint falls back to Code/autopkg in the source tree
            return
        self.copy_file(
            os.path.join("Code", "autopkg"),
            os.path.join(self.build_lib, "autopkgcmd", "autopkg"),
        )


with open("Code/autopkglib/version.plist", "rb") as f:
    setup(
        version=plistlib.load(f)["Version"],
        cmdclass={"build_py": BuildPyWithCLI},
    )
