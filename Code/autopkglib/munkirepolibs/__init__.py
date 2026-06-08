#!/usr/local/autopkg/python
#
# Copyright 2026 Elliot Jordan
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

from autopkglib.munkirepolibs.AutoPkgLib import AutoPkgLib
from autopkglib.munkirepolibs.MunkiLib import MunkiLib


def fetch_repo_library(
    munki_repo, munki_repo_plugin, munkilib_dir, repo_subdirectory, force_munki_lib
):
    """Return the appropriate repo library for the given plugin configuration."""
    if munki_repo_plugin == "FileRepo" and not force_munki_lib:
        return AutoPkgLib(munki_repo, repo_subdirectory)
    else:
        return MunkiLib(munki_repo, munki_repo_plugin, munkilib_dir, repo_subdirectory)
