#!/usr/local/autopkg/python
#
# Copyright 2020 Brian Smith
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

from autopkglib import ProcessorError, find_binary
from autopkglib.ChocolateyPackager import ChocolateyPackager

_ChocolateyPackager_mod = sys.modules[ChocolateyPackager.__module__]

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


class TestChocolateyPackagerPathSafety(unittest.TestCase):
    """Path validation tests that do not require Windows or Chocolatey."""

    def setUp(self):
        self.test_dir = TemporaryDirectory()
        self.choco_path = os.path.join(self.test_dir.name, "choco.exe")
        self.installer_path = os.path.join(self.test_dir.name, "installer.exe")
        open(self.choco_path, "wb").close()
        open(self.installer_path, "wb").close()
        self.good_file_vars: VarDict = {
            "RECIPE_CACHE_DIR": self.test_dir.name,
            "chocoexe_path": self.choco_path,
            "id": "a-package",
            "version": "1.4.4",
            "title": "A package",
            "authors": "package people",
            "description": "Yeah",
            "installer_path": self.installer_path,
            "installer_checksum": "781FBCCE29C1BA769055E3D012A69562",
            "installer_checksum_type": "md5",
            "installer_type": "exe",
        }

    def tearDown(self):
        self.test_dir.cleanup()

    def processor(self, env: VarDict | None = None) -> ChocolateyPackager:
        return ChocolateyPackager(
            env=deepcopy(env or self.good_file_vars),
            infile=BytesIO(),
            outfile=BytesIO(),
        )

    def test_id_and_version_reject_path_traversal_components(self):
        cases = [
            ("id", "../escape"),
            ("id", "nested/name"),
            ("id", r"nested\name"),
            ("version", "../1.4.4"),
            ("version", "nested/1.4.4"),
            ("version", r"nested\1.4.4"),
        ]

        for varname, value in cases:
            with self.subTest(varname=varname, value=value):
                env = deepcopy(self.good_file_vars)
                env[varname] = value
                with unittest.mock.patch("subprocess.Popen") as popen_mock:
                    with self.assertRaisesRegex(
                        ProcessorError,
                        f"Variable `{varname}` may not contain path separators",
                    ):
                        self.processor(env).process()
                    popen_mock.assert_not_called()

    def test_generated_package_paths_stay_under_their_base_directories(self):
        processor = self.processor()
        build_dir = os.path.join(self.test_dir.name, "build")
        output_dir = os.path.join(self.test_dir.name, "output")

        self.assertEqual(processor.idver, "a-package.1.4.4")
        self.assertEqual(
            processor._nuspec_path(build_dir),
            os.path.join(build_dir, "a-package.nuspec"),
        )
        self.assertEqual(
            processor._path_under_dir(output_dir, f"{processor.idver}.log"),
            os.path.join(output_dir, "a-package.1.4.4.log"),
        )

    def test_generated_package_paths_reject_escaping_parts(self):
        processor = self.processor()
        build_dir = os.path.join(self.test_dir.name, "build")

        with self.assertRaisesRegex(ProcessorError, "resolves outside"):
            processor._path_under_dir(build_dir, "..", "escape")

    def test_remote_installer_renders_url_checksum_fields(self):
        env = deepcopy(self.good_file_vars)
        env["installer_url"] = "https://example.com/downloads/installer.exe"
        env["installer_checksum"] = (
            "4A8F3C1B5E6D7A9B0C2D4E6F8A1B3C5D7E9F0A2B4C6D8E1F3A5B7C9D0E2F4A6B"
        )
        env["installer_checksum_type"] = "sha256"
        del env["installer_path"]

        rendered = self.processor(env).chocolateyinstall_ps1().render_str()

        self.assertIn("url = 'https://example.com/downloads/installer.exe'", rendered)
        self.assertIn(f"checksum = '{env['installer_checksum']}'", rendered)
        self.assertIn("checksumType = 'sha256'", rendered)

    def test_remote_installer_requires_checksum_before_packaging(self):
        env = deepcopy(self.good_file_vars)
        env["installer_url"] = "https://example.com/downloads/installer.exe"
        del env["installer_path"]
        del env["installer_checksum"]

        with unittest.mock.patch("subprocess.Popen") as popen_mock:
            with self.assertRaisesRegex(
                ProcessorError,
                "`installer_checksum` is required when `installer_url` is provided",
            ):
                self.processor(env).process()
            popen_mock.assert_not_called()

    def test_nonzero_choco_pack_error_includes_output(self):
        processor = self.processor()
        build_dir = os.path.join(self.test_dir.name, "build")
        output_dir = os.path.join(self.test_dir.name, "output")
        os.mkdir(build_dir)
        os.mkdir(output_dir)

        proc_mock = unittest.mock.Mock()
        proc_mock.communicate.return_value = (
            "choco stdout\nchoco stderr\n",
            None,
        )
        proc_mock.returncode = 2

        with unittest.mock.patch("subprocess.Popen", return_value=proc_mock):
            with self.assertRaises(ProcessorError) as cm:
                processor.choco_pack(build_dir, output_dir)

        self.assertIn("returned: 2", str(cm.exception))
        self.assertIn("choco stdout", str(cm.exception))
        self.assertIn("choco stderr", str(cm.exception))

    def test_main_preserves_build_processor_error(self):
        processor = self.processor()

        with unittest.mock.patch.object(
            processor,
            "write_build_configs",
            side_effect=ProcessorError("specific packaging failure"),
        ):
            with unittest.mock.patch("subprocess.Popen") as popen_mock:
                with self.assertRaisesRegex(
                    ProcessorError,
                    "specific packaging failure",
                ) as cm:
                    processor.process()

        self.assertNotIn("Chocolatey packaging failed unexpectedly", str(cm.exception))
        popen_mock.assert_not_called()


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
            env, infile=BytesIO(), outfile=BytesIO()
        )._write_chocolatey_install(self.test_dir.name)
        self.assertIn("Write-Output 'Test'\n", get_mocked_writes(openfile_mock))


class TestChocolateyPackagerValidation(unittest.TestCase):
    """Tests for validation, defaults, and error handling."""

    def setUp(self):
        self.test_dir = TemporaryDirectory()
        self.choco_path = os.path.join(self.test_dir.name, "choco.exe")
        self.installer_path = os.path.join(self.test_dir.name, "installer.exe")
        open(self.choco_path, "wb").close()
        open(self.installer_path, "wb").close()
        self.good_file_vars: VarDict = {
            "RECIPE_CACHE_DIR": self.test_dir.name,
            "chocoexe_path": self.choco_path,
            "id": "a-package",
            "version": "1.4.4",
            "title": "A package",
            "authors": "package people",
            "description": "Yeah",
            "installer_path": self.installer_path,
            "installer_checksum": "781FBCCE29C1BA769055E3D012A69562",
            "installer_checksum_type": "md5",
            "installer_type": "exe",
        }

    def tearDown(self):
        self.test_dir.cleanup()

    def processor(self, env: VarDict | None = None) -> ChocolateyPackager:
        return ChocolateyPackager(
            env=deepcopy(env or self.good_file_vars),
            infile=BytesIO(),
            outfile=BytesIO(),
        )

    def test_check_enum_var_invalid_installer_type(self):
        from nuget import CHOCO_FILE_TYPES as CHOCO_FILE_TYPES_NUGET

        env = deepcopy(self.good_file_vars)
        env["installer_type"] = "invalid"
        proc = self.processor(env)
        with self.assertRaises(ValueError) as cm:
            proc._check_enum_var("installer_type", CHOCO_FILE_TYPES_NUGET)
        self.assertIn("not one of", str(cm.exception))

    def test_check_enum_var_invalid_checksum_type(self):
        from nuget import CHOCO_CHECKSUM_TYPES

        env = deepcopy(self.good_file_vars)
        env["installer_checksum_type"] = "invalid"
        proc = self.processor(env)
        with self.assertRaises(ValueError):
            proc._check_enum_var("installer_checksum_type", CHOCO_CHECKSUM_TYPES)

    def test_ensure_path_var_not_found(self):
        env = deepcopy(self.good_file_vars)
        env["chocoexe_path"] = os.path.join(self.test_dir.name, "nonexistent.exe")
        proc = self.processor(env)
        with self.assertRaisesRegex(ProcessorError, "not found at"):
            proc._ensure_path_var("chocoexe_path")

    def test_ensure_path_var_with_default_fallback(self):
        env = deepcopy(self.good_file_vars)
        env["pathname"] = self.installer_path
        del env["installer_path"]

        proc = self.processor(env)
        result = proc._ensure_path_var("installer_path", "pathname")
        self.assertEqual(result, os.path.abspath(self.installer_path))

    def test_safe_path_component_rejects_empty_string(self):
        env = deepcopy(self.good_file_vars)
        env["id"] = ""
        proc = self.processor(env)
        with self.assertRaisesRegex(ProcessorError, "non-empty string"):
            proc._safe_path_component("id")

    def test_safe_path_component_rejects_parent_directory_reference(self):
        env = deepcopy(self.good_file_vars)
        env["id"] = ".."
        proc = self.processor(env)
        with self.assertRaisesRegex(ProcessorError, "parent-directory references"):
            proc._safe_path_component("id")

    def test_nuspec_definition_with_dependencies(self):
        env = deepcopy(self.good_file_vars)
        env["dependencies"] = [{"id": "dep1", "version": "1.0"}]
        proc = self.processor(env)
        nuspec = proc.nuspec_definition()
        from nuget import NuspecGenerator

        self.assertIsInstance(nuspec, NuspecGenerator)
        # Verify that the dependency renders into the XML output
        rendered = nuspec.render_str()
        self.assertIn("dep1", rendered)
        self.assertIn("1.0", rendered)

    def test_chocolateyinstall_ps1_with_string_args(self):
        env = deepcopy(self.good_file_vars)
        env["installer_args"] = "/qn"
        proc = self.processor(env)
        gen = proc.chocolateyinstall_ps1()
        rendered = gen.render_str()
        self.assertIn("/qn", rendered)

    def test_log_list_of_messages(self):
        proc = self.processor()
        with unittest.mock.patch.object(proc, "output") as mock_output:
            proc.log(["msg1", "msg2"])
        self.assertEqual(mock_output.call_count, 2)
        mock_output.assert_any_call("msg1", 0)
        mock_output.assert_any_call("msg2", 0)

    def test_main_raises_both_installer_url_and_path(self):
        env = deepcopy(self.good_file_vars)
        env["installer_url"] = "https://example.com/installer.exe"
        # installer_path is already set in good_file_vars (not DefaultValue)
        with self.assertRaisesRegex(ProcessorError, "conflict"):
            self.processor(env).process()

    def test_main_raises_missing_both_installer_url_and_path(self):
        from autopkglib.ChocolateyPackager import DefaultValue

        env = deepcopy(self.good_file_vars)
        # No installer_url, installer_path is DefaultValue, no pathname
        del env["installer_path"]
        env["installer_path"] = DefaultValue
        if "pathname" in env:
            del env["pathname"]
        with self.assertRaises(ProcessorError):
            self.processor(env).process()

    def test_main_raises_invalid_installer_args_type(self):
        env = deepcopy(self.good_file_vars)
        env["installer_args"] = 123
        with self.assertRaisesRegex(ProcessorError, "type list or string"):
            self.processor(env).process()

    def test_chocolateyinstall_ps1_rejects_invalid_installer_args_type(self):
        """Called directly, this should raise ProcessorError, not RuntimeError."""
        env = deepcopy(self.good_file_vars)
        env["installer_args"] = 123
        with self.assertRaisesRegex(ProcessorError, "type list or string"):
            self.processor(env).chocolateyinstall_ps1()

    def test_main_unexpected_exception_wrapped(self):
        proc = self.processor()
        with unittest.mock.patch.object(
            proc, "write_build_configs", side_effect=ValueError("test")
        ):
            with unittest.mock.patch("subprocess.Popen"):
                with self.assertRaisesRegex(
                    ProcessorError, "Chocolatey packaging failed unexpectedly"
                ):
                    proc.process()

    def test_main_keeps_build_directory_when_flag_set(self):
        env = deepcopy(self.good_file_vars)
        env["KEEP_BUILD_DIRECTORY"] = True

        fake_nupkg = os.path.join(self.test_dir.name, "a-package.1.4.4.nupkg")
        open(fake_nupkg, "wb").close()

        proc = self.processor(env)

        with unittest.mock.patch.object(
            proc, "write_build_configs"
        ), unittest.mock.patch.object(
            proc, "choco_pack", return_value=fake_nupkg
        ), unittest.mock.patch.object(
            _ChocolateyPackager_mod, "rmtree"
        ) as mock_rmtree:
            result_env = proc.process()

        mock_rmtree.assert_not_called()
        self.assertIn("choco_build_directory", result_env)
