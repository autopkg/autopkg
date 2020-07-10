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

import unittest
from textwrap import dedent
from typing import Optional, Sequence, Tuple

from nuget import (
    ChocolateyInstallGenerator,
    ChocolateyValidationError,
    NuspecGenerator,
    NuspecValidationError,
)


class TestNuspecGenerator(unittest.TestCase):
    def setUp(self):
        self.maxDiff = 100000

    def test_nuspec_generator_basic_rendering(self):
        expected = dedent(
            """\
<package xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" >
    <metadata>
        <id>test</id>
        <version>0.0.1</version>
        <title>Test software</title>
        <authors>python</authors>
        <description>This is some excellent software</description>
    </metadata>
</package>
        """
        )
        pkg = NuspecGenerator(
            id="test",
            title="Test software",
            version="0.0.1",
            authors="python",
            description="This is some excellent software",
        )
        xml = pkg.render_str()
        self.assertTrue(len(xml) > 0)
        self.assertEquals(expected, xml)

    def test_nuspec_generator_basic_validation(self):
        # Test that our custom field requirement is honored.
        # The `title` field is not mandatory in the XML schema, however packages without
        # a title are rendered confusingly in chocolatey output, so enforce it.
        with self.assertRaises(NuspecValidationError):
            NuspecGenerator(
                id="test", title=None, version="4.4", authors="people", description=""
            )

        # Smoke test that the validation code provided by `generateDS` is working.
        # This test is just to help catch any upstream (NuGet or generateDS) bugs,
        # should they ever occur.
        with self.assertRaises(NuspecValidationError):
            NuspecGenerator(
                id=None, title="", version="4.4", authors="people", description=""
            )


class TestChocolateyInstallGenerator(unittest.TestCase):

    COMMON_HEADER = dedent(
        """\
$ErrorActionPreference = 'Stop'
$toolsDir = "$(Split-Path -Parent $MyInvocation.MyCommand.Definition)\""""
    )

    def setUp(self):
        self.maxDiff = 100000

    def test_basic_validation(self):
        # Only validating error cases for now.
        validation_cases: Sequence[
            Tuple[str, ChocolateyInstallGenerator, Optional[Exception]]
        ] = (
            (
                "empty packageName",
                ChocolateyInstallGenerator("", "msi"),
                ChocolateyValidationError,
            ),
            (
                "invalid fileType",
                ChocolateyInstallGenerator("foopkg", "pkg"),
                ChocolateyValidationError,
            ),
            (
                "missing content",
                ChocolateyInstallGenerator("foopkg", "exe"),
                ChocolateyValidationError,
            ),
            (
                "missing url checksum",
                ChocolateyInstallGenerator(
                    packageName="foopkg",
                    fileType="exe",
                    url="example.com/nochecksum.exe",
                ),
                ChocolateyValidationError,
            ),
            (
                "missing url64bit checksum",
                ChocolateyInstallGenerator(
                    packageName="foopkg",
                    fileType="exe",
                    url64bit="example.com/nochecksum64.exe",
                ),
                ChocolateyValidationError,
            ),
            (
                "invalid checksum type: url",
                ChocolateyInstallGenerator(
                    packageName="foopkg",
                    fileType="exe",
                    url="example.com/nochecksum.exe",
                    checksum="notarealchecksumitsokay",
                    checksumType="unreal2048",
                ),
                ChocolateyValidationError,
            ),
            (
                "invalid checksum type: url",
                ChocolateyInstallGenerator(
                    packageName="foopkg",
                    fileType="exe",
                    url="example.com/nochecksum.exe",
                    checksum="notarealchecksumitsokay",
                    checksumType="sha1",
                ),
                None,
            ),
            (
                "invalid checksum type: url64bit",
                ChocolateyInstallGenerator(
                    packageName="foopkg",
                    fileType="exe",
                    url="example.com/nochecksum64.exe",
                    checksum="notarealchecksumitsokay64",
                    checksumType="unreal2049",
                ),
                ChocolateyValidationError,
            ),
        )
        for casename, object, expectedres in validation_cases:
            with self.subTest(casename):
                if expectedres is not None:
                    self.assertRaises(expectedres, object._validate)
                else:
                    object._validate()

    def test_basic_rendering(self):
        expected = dedent(
            f"""\
{self.COMMON_HEADER}
$file = Join-Path $toolsDir 'fake.installer.exe'
$packageArgs = @{{
  packageName = 'fakepkg'
  fileType = 'exe'
  checksum = 'notarealchecksumitsokay'
  checksumType = 'sha1'
  file = $file
}}

Install-ChocolateyInstallPackage @packageArgs
            """
        )

        self.assertEquals(
            expected,
            ChocolateyInstallGenerator(
                packageName="fakepkg",
                fileType="exe",
                file="C:/convenient/filesystem/path/fake.installer.exe",
                checksum="notarealchecksumitsokay",
                checksumType="sha1",
            ).render_str(),
        )


if __name__ == "__main__":
    unittest.main()
