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
import re
import unittest
import unittest.mock
from copy import deepcopy
from tempfile import TemporaryDirectory
from typing import Any

from autopkglib import ProcessorError
from autopkglib.Unarchiver import Unarchiver
from tests import get_processor_module

UnarchiverModule: Any = get_processor_module(Unarchiver)


class TestUnarchiver(unittest.TestCase):
    def setUp(self):
        self.maxDiff = 100000
        self.tmp_dir = TemporaryDirectory()
        self.default_archive_path = os.path.join(
            self.tmp_dir.name, "archive_path", "is", "irrelevant.zip"
        )
        self.default_destination_path = os.path.join(
            self.tmp_dir.name, "destination_path", "is", "irrelevant"
        )
        self.processor_env: dict[str, Any] = {
            "archive_path": self.default_archive_path,
            "destination_path": self.default_destination_path,
            "purge_destination": False,
            "archive_format": None,
            "RECIPE_CACHE_DIR": self.tmp_dir.name,
            "NAME": "destination_path/FAILURE",
        }
        self.processor = Unarchiver(env=deepcopy(self.processor_env))

        self._popen_patcher = unittest.mock.patch.object(
            UnarchiverModule.subprocess, "Popen", autospec=True
        )
        self.popen_mock = self._popen_patcher.start()
        self.process_mock = self.popen_mock.return_value

        self.addCleanup(unittest.mock.patch.stopall)
        self.addCleanup(self.tmp_dir.cleanup)

    @unittest.mock.patch.object(UnarchiverModule, "is_mac", return_value=True)
    def test_default_extractor_selection_macos(self, _mock):
        """Test that we use utility extraction on macOS."""
        self.assertEqual(False, UnarchiverModule._default_use_python_native_extractor())

    @unittest.mock.patch.object(UnarchiverModule, "is_mac", return_value=False)
    def test_default_extractor_selection_other(self, _mock):
        """Test that we use native extraction on other platforms."""
        self.assertEqual(True, UnarchiverModule._default_use_python_native_extractor())

    @unittest.mock.patch.object(Unarchiver, "_extract")
    def test_extract_called(self, extract_mock):
        """Smoke test the processor with a basic configuration."""
        self.processor.process()
        extract_mock.assert_called_once_with(
            "zip", self.default_archive_path, self.default_destination_path
        )

    def test_utility_extract(self):
        # Ensure that utility extraction is used on any test platform,
        # since it won't actually run.
        self.processor.env["USE_PYTHON_NATIVE_EXTRACTOR"] = False
        self.process_mock.communicate.return_value = ("", "")
        self.process_mock.returncode = 0

        utility_cases: list[tuple[str, str, str | None]] = [
            ("autodetects zip format", "/usr/bin/ditto", None),
            ("manual zip", "/usr/bin/ditto", "zip"),
            ("manual tar.gz", "/usr/bin/tar", "tar_gzip"),
            ("manual tar.bz2", "/usr/bin/tar", "tar_bzip2"),
            ("manual gzip", "/usr/bin/ditto", "gzip"),
        ]

        for subtest_name, expected_binary, archive_format in utility_cases:
            with self.subTest(subtest_name, expected_binary=expected_binary):
                self.processor.env["archive_format"] = archive_format
                self.processor.process()
                self.popen_mock.assert_called()
                self.process_mock.communicate.assert_called()

                # Checks the first value of the first positional argument.
                self.assertEqual(expected_binary, self.popen_mock.call_args[0][0][0])

    def test_native_extract(self):
        # Ensure that native extraction is used on any test platform,
        # since it won't actually run.
        self.processor.env["USE_PYTHON_NATIVE_EXTRACTOR"] = True

        zipfile_mock = unittest.mock.MagicMock(spec=UnarchiverModule.zipfile.ZipFile)
        tarfile_mock = unittest.mock.MagicMock(spec=UnarchiverModule.tarfile.TarFile)
        native_cases: list[
            tuple[str, UnarchiverModule.ExtractorType, str | None, str]
        ] = [
            ("autodetects zip format", zipfile_mock, None, "zip"),
            ("manual zip", zipfile_mock, "zip", "zip"),
            ("manual tar.gz", tarfile_mock, "tar_gzip", "tar_gzip"),
            ("manual tar.bz2", tarfile_mock, "tar_bzip2", "tar_bzip2"),
        ]

        for (
            subtest_name,
            expected_class,
            forced_archive_format,
            auto_archive_format,
        ) in native_cases:
            with unittest.mock.patch.dict(
                UnarchiverModule.NATIVE_EXTRACTORS,
                {auto_archive_format: expected_class},
                clear=True,
            ):
                with self.subTest(subtest_name, expected_class=expected_class):
                    self.processor.env["archive_format"] = forced_archive_format
                    self.processor.process()
                    expected_class.assert_called_with(
                        self.processor.env["archive_path"], mode="r"
                    )
                    expected_class.return_value.extractall.assert_called()

        self.popen_mock.assert_not_called()

    # ---------------------------------------------------------------------------
    # get_archive_format
    # ---------------------------------------------------------------------------

    def test_get_archive_format_unknown_extension(self):
        """Unknown extension returns None."""
        result = self.processor.get_archive_format("file.xyz")
        self.assertIsNone(result)

    # ---------------------------------------------------------------------------
    # _validate_archive_members
    # ---------------------------------------------------------------------------

    def test_validate_archive_members_directory_traversal_attack(self):
        """Directory traversal path raises ProcessorError."""

        dest = os.path.join(os.sep, "safe", "destination")
        evil_name = "../../../etc/passwd"

        member_mock = unittest.mock.MagicMock()
        member_mock.name = evil_name
        archive_mock = unittest.mock.MagicMock(spec=UnarchiverModule.tarfile.TarFile)
        archive_mock.getmembers.return_value = [member_mock]

        def fake_realpath(p):
            if p == dest:
                return dest
            return os.path.join(os.sep, "etc", "passwd")

        with unittest.mock.patch.object(
            UnarchiverModule.os.path, "realpath", side_effect=fake_realpath
        ):
            with self.assertRaises(ProcessorError) as ctx:
                self.processor._validate_archive_members(archive_mock, dest)

        self.assertIn("extract outside destination directory", str(ctx.exception))

    def test_validate_archive_members_unknown_archive_type(self):
        """Archive with neither getmembers nor namelist returns silently."""
        archive_mock = unittest.mock.MagicMock(spec=[])  # no attributes
        # Should not raise
        self.processor._validate_archive_members(archive_mock, "/some/dest")

    def test_validate_archive_members_zipfile(self):
        """zipfile path with safe members completes without error."""
        dest = self.tmp_dir.name
        archive_mock = unittest.mock.MagicMock(spec=UnarchiverModule.zipfile.ZipFile)
        archive_mock.namelist.return_value = ["safe/path/file.txt"]

        def fake_realpath(p):
            if p.endswith("file.txt"):
                return os.path.join(dest, "safe", "path", "file.txt")
            return p

        with unittest.mock.patch.object(
            UnarchiverModule.os.path, "realpath", side_effect=fake_realpath
        ):
            # Should not raise
            self.processor._validate_archive_members(archive_mock, dest)

    # ---------------------------------------------------------------------------
    # main() — missing archive_path
    # ---------------------------------------------------------------------------

    def test_main_missing_archive_path(self):
        """Missing archive_path and pathname raises ProcessorError."""

        self.processor.env.pop("archive_path", None)
        self.processor.env.pop("pathname", None)
        with self.assertRaises(ProcessorError) as ctx:
            self.processor.main()
        self.assertIn("archive_path", str(ctx.exception))

    # ---------------------------------------------------------------------------
    # main() — makedirs OSError
    # ---------------------------------------------------------------------------

    def test_main_makedirs_oserror(self):
        """os.makedirs OSError raises ProcessorError with 'Can't create'."""

        non_existent = os.path.join(self.tmp_dir.name, "no_such_dir", "dest")
        self.processor.env["destination_path"] = non_existent

        err = OSError()
        err.strerror = "Permission denied"
        with unittest.mock.patch.object(
            UnarchiverModule.os, "makedirs", side_effect=err
        ):
            with self.assertRaises(ProcessorError) as ctx:
                self.processor.main()
        self.assertIn("Can't create", str(ctx.exception))

    # ---------------------------------------------------------------------------
    # main() — purge_destination OSErrors
    # ---------------------------------------------------------------------------

    def test_main_purge_destination_file_removal_oserror(self):
        """Unlink failure during purge raises ProcessorError with 'Can't remove'."""

        dest = os.path.join(self.tmp_dir.name, "purge_dest_file")
        os.makedirs(dest)
        open(os.path.join(dest, "dummy.txt"), "w").close()

        self.processor.env["destination_path"] = dest
        self.processor.env["purge_destination"] = True

        err = OSError()
        err.strerror = "Permission denied"
        with unittest.mock.patch.object(UnarchiverModule.os, "unlink", side_effect=err):
            with self.assertRaises(ProcessorError) as ctx:
                self.processor.main()
        self.assertIn("Can't remove", str(ctx.exception))

    def test_main_purge_destination_directory_removal_oserror(self):
        """rmtree failure during purge raises ProcessorError with 'Can't remove'."""

        dest = os.path.join(self.tmp_dir.name, "purge_dest_dir")
        os.makedirs(dest)
        os.makedirs(os.path.join(dest, "subdir"))

        self.processor.env["destination_path"] = dest
        self.processor.env["purge_destination"] = True

        err = OSError()
        err.strerror = "Permission denied"
        with unittest.mock.patch.object(
            UnarchiverModule.shutil, "rmtree", side_effect=err
        ):
            with self.assertRaises(ProcessorError) as ctx:
                self.processor.main()
        self.assertIn("Can't remove", str(ctx.exception))

    # ---------------------------------------------------------------------------
    # main() — unknown/invalid archive format
    # ---------------------------------------------------------------------------

    def test_main_cannot_guess_archive_format(self):
        """Unrecognized extension with no explicit format raises ProcessorError."""

        dest = os.path.join(self.tmp_dir.name, "dest_guess")
        os.makedirs(dest)
        self.processor.env["archive_path"] = os.path.join(self.tmp_dir.name, "file.xyz")
        self.processor.env["destination_path"] = dest
        self.processor.env["archive_format"] = None

        with self.assertRaises(ProcessorError) as ctx:
            self.processor.main()
        self.assertIn("Can't guess archive format", str(ctx.exception))

    def test_main_invalid_archive_format(self):
        """Explicit unrecognised format raises ProcessorError."""

        dest = os.path.join(self.tmp_dir.name, "dest_invalid")
        os.makedirs(dest)
        self.processor.env["destination_path"] = dest
        self.processor.env["archive_format"] = "invalid_format"

        with self.assertRaises(ProcessorError) as ctx:
            self.processor.main()
        self.assertIn(
            "'invalid_format' is not valid for the 'archive_format' variable",
            str(ctx.exception),
        )

    # ---------------------------------------------------------------------------
    # _extract_utility — OSError and non-zero return code
    # ---------------------------------------------------------------------------

    def test_extract_utility_oserror(self):
        """Popen OSError raises ProcessorError with 'execution failed with error code'."""

        self.processor.env["USE_PYTHON_NATIVE_EXTRACTOR"] = False

        err = OSError()
        err.errno = 13
        err.strerror = "Permission denied"
        self.popen_mock.side_effect = err

        with self.assertRaises(ProcessorError) as ctx:
            self.processor._extract_utility(
                "zip", self.default_archive_path, self.default_destination_path
            )
        self.assertIn("execution failed with error code 13", str(ctx.exception))

    def test_extract_utility_nonzero_returncode(self):
        """Non-zero returncode raises ProcessorError with stderr message."""

        self.processor.env["USE_PYTHON_NATIVE_EXTRACTOR"] = False
        self.process_mock.communicate.return_value = ("", "tar: unable to open archive")
        self.process_mock.returncode = 1

        with self.assertRaises(ProcessorError) as ctx:
            self.processor._extract_utility(
                "tar_gzip", self.default_archive_path, self.default_destination_path
            )
        self.assertRegex(
            str(ctx.exception),
            re.compile(r"Unarchiving.*failed: tar: unable to open archive"),
        )

    # ---------------------------------------------------------------------------
    # _extract_native — exception during extraction
    # ---------------------------------------------------------------------------

    def test_extract_native_exception(self):
        """Exception during native extraction raises ProcessorError."""

        self.processor.env["USE_PYTHON_NATIVE_EXTRACTOR"] = True

        archive_instance = unittest.mock.MagicMock(
            spec=UnarchiverModule.tarfile.TarFile
        )
        archive_instance.extractall.side_effect = Exception("corrupted archive")
        archive_instance.getmembers.return_value = []

        # Patch NATIVE_EXTRACTORS so _extract_native calls our mock class
        mock_class = unittest.mock.MagicMock(return_value=archive_instance)
        with unittest.mock.patch.dict(
            UnarchiverModule.NATIVE_EXTRACTORS, {"tar_gzip": mock_class}
        ):
            with self.assertRaises(ProcessorError) as ctx:
                self.processor._extract_native(
                    "tar_gzip",
                    self.default_archive_path,
                    self.default_destination_path,
                )
        self.assertRegex(
            str(ctx.exception),
            re.compile(r"Unarchiving.*failed: corrupted archive"),
        )
