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

from io import StringIO
from typing import Optional, Sequence, TextIO

from nuget.generated._nuspec import (
    GdsCollector_,
    contentFilesType,
    dependenciesType,
    dependency,
    licenseType,
    metadataType,
    package,
)

__all__ = ["NuspecGenerator", "NuspecValidationError"]


class NuspecValidationError(Exception):
    def __init__(self, msg: str, *errors: str) -> None:
        super().__init__(msg)
        self.msg: str = msg
        self.errors: Sequence[str] = errors

    def __str__(self) -> str:
        return f"{self.msg}. Problems: {', '.join(self.errors)}"


class NuspecGenerator(package):
    """NuspecGenerator is a thin wrapper around the `_nuspec.package` generated class.
    """

    def __init__(
        self,
        id: str,
        title: str,  # title is not actually required by Nuspec, but it should be.
        version: str,
        authors: str,
        description: str,
        owners: Optional[str] = None,
        licenseUrl: Optional[str] = None,
        projectUrl: Optional[str] = None,
        iconUrl: Optional[str] = None,
        summary: Optional[str] = None,
        releaseNotes: Optional[str] = None,
        copyright: Optional[str] = None,
        tags: Optional[str] = None,
        icon: Optional[str] = None,
        license: Optional[licenseType] = None,
        dependencies: Optional[Sequence[dependency]] = None,
        contentFiles: Optional[contentFilesType] = None,
    ):
        if not isinstance(title, str):
            raise NuspecValidationError("Argument 'title' must be a string")

        super().__init__(
            metadataType(
                id=id,
                version=version,
                title=title,
                authors=authors,
                owners=owners,
                licenseUrl=licenseUrl,
                projectUrl=projectUrl,
                iconUrl=iconUrl,
                description=description,
                summary=summary,
                releaseNotes=releaseNotes,
                copyright=copyright,
                tags=tags,
                icon=icon,
                license=license,
                dependencies=dependenciesType(dependency=dependencies),
                contentFiles=contentFiles,
            )
        )
        self.validate()

    def validate(self) -> None:
        """Ensures that the definition is well-formed according to the Nuspec
        XML schema definition. See Scripts\regenerate_nuspec.ds.py for more details."""
        err_collector = GdsCollector_()
        if not self.validate_(err_collector, recursive=True):
            raise NuspecValidationError(
                "Invalid NugetPackage specification", *err_collector.get_messages()
            )

    def render_to(self, out: TextIO) -> None:
        """Writes pretty-printed XML of the Nuget package definition to `out`.
        """
        # Call validate before export, as the definition may have been changed.
        # For example, by a call to `NuspecGenerator.metadata.set_dependencies`.
        self.validate()
        self.export(out, level=0)

    def render_str(self) -> str:
        """Render pretty-printed XML and return a `str` representation."""
        out = StringIO()
        self.render_to(out)
        return out.getvalue()
