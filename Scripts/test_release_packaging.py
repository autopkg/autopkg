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

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

AUTOPKG_ROOT = Path(__file__).parents[1]
RELEASE_SCRIPT_PATH = AUTOPKG_ROOT / "Scripts" / "make_new_release.py"

spec = importlib.util.spec_from_file_location("make_new_release", RELEASE_SCRIPT_PATH)
make_new_release = importlib.util.module_from_spec(spec)
sys.modules["make_new_release"] = make_new_release
spec.loader.exec_module(make_new_release)


def create_packaged_python(root: str, version: str = "Current") -> tuple[str, str]:
    framework_path = (
        Path(root) / "expanded" / "Library" / "AutoPkg" / "Python3" / "Python.framework"
    )
    python_path = (
        framework_path
        / "Versions"
        / version
        / "Resources"
        / "Python.app"
        / "Contents"
        / "MacOS"
        / "Python"
    )
    python_path.parent.mkdir(parents=True)
    python_path.touch()
    return str(framework_path), str(python_path)


class TestReleasePackagingRequirements(unittest.TestCase):
    def test_launchservices_is_direct_macos_requirement(self):
        requirements_in = AUTOPKG_ROOT / "requirements.in"
        entries = [
            line.strip()
            for line in requirements_in.read_text(encoding="utf-8").splitlines()
            if line.strip().lower().startswith("pyobjc-framework-launchservices")
        ]

        self.assertEqual(
            entries, ["pyobjc-framework-LaunchServices; sys_platform == 'darwin'"]
        )


class TestBundledPythonSmokeTest(unittest.TestCase):
    def test_find_bundled_python_finds_framework_executable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            framework_path, python_path = create_packaged_python(temp_dir)

            self.assertEqual(
                make_new_release.find_bundled_python(temp_dir),
                (framework_path, python_path),
            )

    def test_find_bundled_python_finds_versioned_framework_executable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            framework_path, python_path = create_packaged_python(temp_dir, "3.11")

            self.assertEqual(
                make_new_release.find_bundled_python(temp_dir),
                (framework_path, python_path),
            )

    def test_bundled_python_binary_paths_returns_framework_binaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            framework_path = Path(temp_dir) / "Python.framework"
            paths = [
                framework_path / "Versions" / "3.11" / "lib" / "module.so",
                framework_path / "Versions" / "3.11" / "lib" / "libpython.dylib",
                framework_path
                / "Versions"
                / "3.11"
                / "Resources"
                / "Python.app"
                / "Contents"
                / "MacOS"
                / "Python",
                framework_path / "Versions" / "Current" / "bin" / "python3.11",
                framework_path / "Versions" / "Current" / "Python",
                framework_path / "Versions" / "Current" / "bin" / "python3.11-config",
                framework_path / "Versions" / "3.11" / "README.txt",
            ]
            for path in paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()

            self.assertEqual(
                make_new_release.bundled_python_binary_paths(str(framework_path)),
                sorted(str(path) for path in paths[:-2]),
            )

    def test_smoke_test_imports_required_pyobjc_frameworks(self):
        calls = []

        def fake_exists(path):
            if path in ("/usr/sbin/pkgutil", "/usr/bin/lipo"):
                return False
            return Path(path).exists()

        def fake_run(args, **kwargs):
            calls.append(args)
            if "--expand-full" in args:
                create_packaged_python(args[-1])
            if "-archs" in args:
                return subprocess.CompletedProcess(
                    args, 0, stdout="x86_64 arm64\n", stderr=""
                )
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        with (
            patch.object(make_new_release.os.path, "exists", side_effect=fake_exists),
            patch.object(
                make_new_release,
                "which",
                side_effect=lambda name: f"/usr/bin/{name}",
            ),
            patch.object(make_new_release.subprocess, "run", side_effect=fake_run),
        ):
            make_new_release.smoke_test_bundled_python("/tmp/autopkg.pkg")

        self.assertEqual(
            calls[0],
            [
                "/usr/bin/pkgutil",
                "--expand-full",
                "/tmp/autopkg.pkg",
                calls[0][-1],
            ],
        )
        self.assertEqual(
            calls[1][1],
            "-c",
        )
        for module_name in (
            "Foundation",
            "Quartz",
            "Security",
            "SystemConfiguration",
            "LaunchServices",
        ):
            self.assertIn(module_name, calls[1][2])
        self.assertEqual(calls[2][1], "-archs")

    def test_smoke_test_reports_pyobjc_import_failures(self):
        def fake_run(args, **kwargs):
            if "--expand-full" in args:
                create_packaged_python(args[-1])
                return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
            return subprocess.CompletedProcess(
                args, 1, stdout="", stderr="LaunchServices: missing"
            )

        with (
            patch.object(make_new_release, "which", return_value="/usr/bin/pkgutil"),
            patch.object(make_new_release.subprocess, "run", side_effect=fake_run),
            self.assertRaises(SystemExit) as err,
        ):
            make_new_release.smoke_test_bundled_python("/tmp/autopkg.pkg")

        self.assertIn("LaunchServices: missing", str(err.exception))

    def test_architecture_smoke_test_fails_when_binary_is_missing_slice(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            framework_path = Path(temp_dir) / "Python.framework"
            module_path = framework_path / "Versions" / "3.11" / "lib" / "bad.so"
            module_path.parent.mkdir(parents=True)
            module_path.touch()

            def fake_run(args, **kwargs):
                return subprocess.CompletedProcess(args, 0, stdout="arm64\n", stderr="")

            with (
                patch.object(make_new_release.subprocess, "run", side_effect=fake_run),
                self.assertRaises(SystemExit) as err,
            ):
                make_new_release.smoke_test_bundled_python_architectures(
                    str(framework_path)
                )

        self.assertIn("missing x86_64", str(err.exception))

    def test_smoke_test_fails_when_packaged_python_is_missing(self):
        def fake_run(args, **kwargs):
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        with (
            patch.object(make_new_release, "which", return_value="/usr/bin/pkgutil"),
            patch.object(make_new_release.subprocess, "run", side_effect=fake_run),
            self.assertRaises(SystemExit) as err,
        ):
            make_new_release.smoke_test_bundled_python("/tmp/autopkg.pkg")

        self.assertEqual(
            str(err.exception),
            "Could not find bundled AutoPkg Python in built package.",
        )


if __name__ == "__main__":
    unittest.main()
