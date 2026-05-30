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
from collections.abc import Sequence
from textwrap import dedent

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
        expected = dedent("""\
<package xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" >
    <metadata>
        <id>test</id>
        <version>0.0.1</version>
        <title>Test software</title>
        <authors>python</authors>
        <description>This is some excellent software</description>
        <dependencies/>
    </metadata>
</package>
        """)
        pkg = NuspecGenerator(
            id="test",
            title="Test software",
            version="0.0.1",
            authors="python",
            description="This is some excellent software",
        )
        xml = pkg.render_str()
        self.assertTrue(len(xml) > 0)
        self.assertEqual(expected, xml)

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
    COMMON_HEADER = dedent("""\
$ErrorActionPreference = 'Stop'
$toolsDir = "$(Split-Path -Parent $MyInvocation.MyCommand.Definition)\"""")

    def setUp(self):
        self.maxDiff = 100000

    def test_basic_validation(self):
        # Only validating error cases for now.
        validation_cases: Sequence[
            tuple[str, ChocolateyInstallGenerator, Exception | None]
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
        expected = dedent(f"""\
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

            """)

        self.assertEqual(
            expected,
            ChocolateyInstallGenerator(
                packageName="fakepkg",
                fileType="exe",
                file="C:/convenient/filesystem/path/fake.installer.exe",
                checksum="notarealchecksumitsokay",
                checksumType="sha1",
            ).render_str(),
        )

    def test_string_fields_escape_single_quotes(self):
        rendered = ChocolateyInstallGenerator(
            packageName="fake'pkg",
            fileType="exe",
            silentArgs="/S /D=/Applications/Bob's App",
            url="https://example.com/downloads/Bob's App.exe",
            checksum="notarealchecksumitsokay",
            checksumType="sha1",
        ).render_str()

        self.assertIn("packageName = 'fake''pkg'", rendered)
        self.assertIn("silentArgs = '/S /D=/Applications/Bob''s App'", rendered)
        self.assertIn("url = 'https://example.com/downloads/Bob''s App.exe'", rendered)

    def test_file_basenames_escape_single_quotes(self):
        rendered = ChocolateyInstallGenerator(
            packageName="fakepkg",
            fileType="exe",
            file="C:/convenient/filesystem/path/Bob's Installer.exe",
            file64="C:/convenient/filesystem/path/Alice's Installer.exe",
        ).render_str()

        self.assertIn("$file = Join-Path $toolsDir 'Bob''s Installer.exe'", rendered)
        self.assertIn(
            "$file64 = Join-Path $toolsDir 'Alice''s Installer.exe'", rendered
        )

    def test_list_values_render_elements_by_type(self):
        generator = ChocolateyInstallGenerator(
            packageName="fakepkg",
            fileType="exe",
            file="fake.installer.exe",
        )

        self.assertEqual(
            "@(0,'can''t',$False)",
            generator._render_field("futureList", [0, "can't", False], []),
        )


if __name__ == "__main__":
    unittest.main()
