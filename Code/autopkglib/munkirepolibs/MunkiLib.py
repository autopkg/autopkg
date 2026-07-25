#!/usr/local/autopkg/python
#
# Copyright 2020 Taylor Boyko
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
import sys
from urllib.parse import urlparse

from autopkglib import ProcessorError


class MunkiLib:
    def __init__(self, munki_repo, munki_repo_plugin, munkilib_dir, repo_subdirectory):
        self.repo_subdirectory = repo_subdirectory
        self.munki_repo = munki_repo

        sys.path.insert(0, munkilib_dir)
        try:
            from munkilib import munkirepo
            from munkilib.admin import munkiimportlib
            from munkilib.cliutils import path2url
        except ImportError as err:
            if not os.path.isdir(os.path.join(munkilib_dir, "munkilib")):
                # munkilib ships in munkitools_pythonlibs, which the Munki 7 Swift
                # tools no longer need at runtime and a future Munki release may
                # stop installing.
                raise ProcessorError(
                    f"munkilib not found in {munkilib_dir}. It is installed by the "
                    "munkitools_pythonlibs package; install that package, or point "
                    "MUNKILIB_DIR at the directory containing munkilib."
                ) from err
            raise ProcessorError(
                f"munkilib import error: {str(err)}\nMunki tools version 3.2.0.3462 "
                "through 6.7.1 is required."
            ) from err

        # if munki_repo is a filesystem path, convert it to a format that is understood by
        # munkirepo.
        if urlparse(munki_repo).scheme == "":
            munki_repo = path2url(munki_repo)

        # Initialize repo. In some cases (FileRepo) this will check to see if the file
        # path exists. In other cases (like GitFileRepo, MWA2APIRepo) this only
        # initializes the repo object and does not actually connect.
        self.repo = munkirepo.connect(munki_repo, munki_repo_plugin)
        self.munkiimportlib = munkiimportlib

    def _full_path(self, path) -> str:
        return os.path.join(self.munki_repo, path)

    def make_catalog_db(self) -> dict:
        return self.munkiimportlib.make_catalog_db(self.repo)

    def copy_pkg_to_repo(self, pkginfo, pkg_path) -> str:
        uploaded_path = self.munkiimportlib.copy_item_to_repo(
            self.repo, pkg_path, pkginfo.get("version"), self.repo_subdirectory
        )

        return self._full_path(uploaded_path)

    # includes '/pkgsinfo' in uploaded path
    def copy_pkginfo_to_repo(self, pkginfo, file_extension="plist") -> str:
        uploaded_path = self.munkiimportlib.copy_pkginfo_to_repo(
            self.repo, pkginfo, self.repo_subdirectory
        )

        return self._full_path(uploaded_path)

    def find_matching_icon(self, pkginfo) -> str | None:
        if self.munkiimportlib.icon_exists_in_repo(self.repo, pkginfo):
            path = self.munkiimportlib.get_icon_path(pkginfo)
            return self._full_path(path)

        return None

    def put_pkginfo_to_repo(self, pkginfo, pkginfo_path) -> None:
        """Updates an existing pkginfo file in the repo via the repo plugin."""
        try:
            from munkilib import FoundationPlist

            relative_path = os.path.relpath(pkginfo_path, self.munki_repo)
            content = FoundationPlist.writePlistToString(pkginfo)
            self.repo.put(relative_path, content)
        except Exception as err:
            raise ProcessorError(
                f"Could not write pkginfo {pkginfo_path}: {err}"
            ) from err

    def extract_and_copy_icon_to_repo(
        self, pkg_path, pkginfo, import_multiple=True
    ) -> str | None:
        uploaded_path = self.munkiimportlib.extract_and_copy_icon(
            self.repo, pkg_path, pkginfo, import_multiple
        )

        if uploaded_path:
            return self._full_path(uploaded_path)

        return None
