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

from .ChocolateyInstallGenerator import (
    CHOCO_CHECKSUM_TYPES,
    CHOCO_FILE_TYPES,
    ChocolateyInstallGenerator,
    ChocolateyValidationError,
)
from .generated._nuspec import dependency as NuspecDependency
from .NuspecGenerator import NuspecGenerator, NuspecValidationError

__all__ = [
    "CHOCO_CHECKSUM_TYPES",
    "CHOCO_FILE_TYPES",
    "ChocolateyInstallGenerator",
    "ChocolateyValidationError",
    "NuspecDependency",
    "NuspecGenerator",
    "NuspecValidationError",
]
