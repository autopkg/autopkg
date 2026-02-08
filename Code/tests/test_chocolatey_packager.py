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
import subprocess
import sys
import unittest
import unittest.mock
from copy import deepcopy
from io import BytesIO
from tempfile import TemporaryDirectory
from typing import Any

from autopkglib import find_binary
from autopkglib.ChocolateyPackager import ChocolateyPackager

VarDict = dict[str, Any]


def get_mocked_writes(mock: unittest.mock.MagicMock) -> str:
    res = ""
    for name, args, _ in mock.mock_calls:
        if name != "().write":
            continue
        res += args[0]
    return res


def check_for_choco() -> bool:
    try:
        return (
            subprocess.run(
                [r"C:\ProgramData\chocolatey\bin\choco.exe", "--version"]
            ).returncode
            == 0
        )
    except FileNotFoundError:
        pass
    return False


@unittest.skipUnless(sys.platform.startswith("win"), "requires Windows")
@unittest.skipUnless(check_for_choco(), "requires chocolatey")
class TestChocolateyPackager(unittest.TestCase):
    """Integration tests that we're actually able to build a package successfully."""

    def setUp(self):
        self.maxDiff = 100000
        self.test_dir = TemporaryDirectory()
        self.common_nuspec_vars: VarDict = {
            "id": "a-package",
            "version": "1.4.4",
            "title": "A package",
            "authors": "package people",
            "description": "Yeah",
        }
        self.common_processor_vars: VarDict = {
            "RECIPE_CACHE_DIR": self.test_dir.name,  # Don't write to real recipe cache.
            "KEEP_BUILD_DIRECTORY": True,  # `self.test_dir` destruction cleans all.
            "chocoexe_path": find_binary("choco"),
        }
        self.installation_file: str = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "autopkg")
        )
        self.good_chocolatey_file_vars: VarDict = {
            "installer_path": self.installation_file,
            "installer_checksum": "781FBCCE29C1BA769055E3D012A69562",
            "installer_checksum_type": "md5",
            "installer_type": "exe",  # a lie, but it's not going to matter
            "output_directory": self.test_dir.name,
        }

        self.good_file_vars: VarDict = {
            **self.common_processor_vars,
            **self.common_nuspec_vars,
            **self.good_chocolatey_file_vars,
        }

    def test_file_installer_build(self):
        processor = ChocolateyPackager(
            env=deepcopy(self.good_file_vars), infile=BytesIO(), outfile=BytesIO()
        )
        result_env: VarDict = processor.process()
        self.assertIn("nuget_package_path", result_env)
        self.assertIn("choco_build_directory", result_env)
        self.assertEqual(
            result_env["nuget_package_path"],
            os.path.join(self.test_dir.name, "a-package.1.4.4.nupkg"),
        )
        os.stat(os.path.join(self.test_dir.name, "a-package.1.4.4.nupkg"))
        os.stat(os.path.join(result_env["choco_build_directory"], "tools", "autopkg"))

    def test_pathname_variable_defaulting(self):
        """Test usage of `pathname` variable as default when present."""

        env = deepcopy(self.good_file_vars)
        env["pathname"] = env["installer_path"]
        del env["installer_path"]

        result_env: VarDict = ChocolateyPackager(
            env, infile=BytesIO(), outfile=BytesIO()
        ).process()

        os.stat(os.path.join(result_env["choco_build_directory"], "tools", "autopkg"))
        self.assertEqual(
            result_env.get(
                "nuget_package_path", "nuget_package_path_NOT-FOUND-IN-RESULT"
            ),
            os.path.join(self.test_dir.name, "a-package.1.4.4.nupkg"),
        )

    @unittest.mock.patch("builtins.open", new_callable=unittest.mock.mock_open)
    def test_additional_actions(self, openfile_mock):
        env = deepcopy(self.good_file_vars)
        env["additional_install_actions"] = "Write-Output 'Test'\n"
        ChocolateyPackager(
            env, infile=BytesIO(), outfile=BytesIO
        )._write_chocolatey_install(self.test_dir.name)
        self.assertIn("Write-Output 'Test'\n", get_mocked_writes(openfile_mock))
