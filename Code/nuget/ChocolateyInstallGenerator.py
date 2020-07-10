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

import os
from dataclasses import dataclass
from io import StringIO
from typing import Any, Dict, List, Optional, Sequence, TextIO

# Constants for various argument constraints derived from
# https://chocolatey.org/docs/helpers-install-chocolatey-package
CHOCO_CHECKSUM_TYPES: Sequence[str] = ("md5", "sha1", "sha256", "sha512")
CHOCO_FILE_TYPES: Sequence[str] = ("exe", "msi", "msu")


class ChocolateyValidationError(Exception):
    pass


@dataclass
class ChocolateyInstallGenerator:
    """
    This will render a chocolateyinstall.ps1 file given some inputs:
    https://chocolatey.org/docs/helpers-install-chocolatey-package

    The generation of the script is intentionally naive and likely
    can only handle the simplest of use cases.
    """

    packageName: str
    fileType: str
    silentArgs: Optional[str] = None
    url: Optional[str] = None
    url64bit: Optional[str] = None
    validExitCodes: Optional[List[int]] = None
    checksum: Optional[str] = None
    checksumType: Optional[str] = None
    checksum64: Optional[str] = None
    checksumType64: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    file: Optional[str] = None
    file64: Optional[str] = None
    useOnlyPackageSilentArguments: Optional[bool] = None
    useOriginalLocation: Optional[bool] = None

    def render_str(self) -> str:
        """Render `chocolateyInstall.ps1` and return a `str` representation."""
        out = StringIO()
        self.render_to(out)
        return out.getvalue()

    def render_to(self, out: TextIO) -> None:
        """Writes a `chocolateyInstall.ps1` file to `out`.
        """
        self._validate()
        preamble_lines: List[str] = []
        splat: str = "$ErrorActionPreference = 'Stop'\n"
        splat += (
            '$toolsDir = "$(Split-Path -Parent $MyInvocation.MyCommand.Definition)"\n'
        )
        args_splat: str = "$packageArgs = @{\n"
        for k, v in self.__dict__.items():
            if v is None:
                continue
            value = self._render_field(k, v, preamble_lines)
            args_splat += f"  {k} = {value}\n"
        args_splat += "}\n\n"
        splat += "\n".join(preamble_lines) + "\n"
        splat += args_splat

        # When a installer file is embedded, we have to use a different install command.
        if self.file or self.file64:
            splat += "Install-ChocolateyInstallPackage @packageArgs\n"
        else:
            splat += "Install-ChocolateyPackage @packageArgs\n"
        out.write(splat)

    def _render_field(self, key: str, value: Any, preamble_lines: List[str]) -> str:
        # If a file parameter is used, fix it up to be relative to the computed
        # tools directory _at the time choco install_ runs.
        if key in ("file", "file64"):
            preamble_lines.append(
                f"${key} = Join-Path $toolsDir '{os.path.basename(value)}'"
            )
            return f"${key}"
        elif isinstance(value, str):
            return f"'{value}'"
        elif isinstance(value, List):
            return f"@({','.join([x.__str__() for x in value])})"
        elif isinstance(value, bool):
            return f"${value}"
        raise ValueError(f"Unhandled value type: {type(value)}")

    def _validate(self) -> None:
        if self.packageName == "":
            raise ChocolateyValidationError("`packageName` must be a non-empty string")

        if self.fileType not in CHOCO_FILE_TYPES:
            raise ChocolateyValidationError(
                f"`fileType`: expected one of: {', '.join(CHOCO_FILE_TYPES)} "
                f"got: '{self.fileType}'"
            )

        if (
            self.url is None
            and self.file is None
            and self.url64bit is None
            and self.file64 is None
        ):
            raise ChocolateyValidationError(
                "One of `file`, `url`, `file64`, or `url64bit` is required"
            )

        if self.url is not None and self.checksum is None:
            raise ChocolateyValidationError(
                "When specifying `url`, `checksum` is required."
            )

        if self.url64bit is not None and self.checksum64 is None:
            raise ChocolateyValidationError(
                "When specifying `url64bit`, `checksum64` is required."
            )

        if self.checksum is not None and self.checksumType not in CHOCO_CHECKSUM_TYPES:
            raise ChocolateyValidationError(
                f"`checksum`: expected one of: {', '.join(CHOCO_CHECKSUM_TYPES)} "
                f"got:' {self.checksum}'"
            )

        if (
            self.checksum64 is not None
            and self.checksumType64 not in CHOCO_CHECKSUM_TYPES
        ):
            raise ChocolateyValidationError(
                f"`checksum64`: expected one of: {', '.join(CHOCO_CHECKSUM_TYPES)} "
                f"got: '{self.checksum64}'"
            )
