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
import unittest.mock
from copy import deepcopy
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Optional, Tuple

from autopkglib.Unarchiver import Unarchiver
from tests import get_processor_module

UnarchiverModule: Any = get_processor_module(Unarchiver)


class TestUnarchiver(unittest.TestCase):
    def setUp(self):
        self.maxDiff = 100000
        self.tempdir = TemporaryDirectory()
        self.default_archive_path = (
            f"{self.tempdir.name}/archive_path/is/irrelevant.zip"
        )
        self.default_destination_path = (
            f"{self.tempdir.name}/destination_path/is/irrelevant"
        )
        self.processor_env: Dict[str, Any] = {
            "archive_path": self.default_archive_path,
            "destination_path": self.default_destination_path,
            "purge_destination": False,
            "archive_format": None,
            "RECIPE_CACHE_DIR": self.tempdir.name,
            "NAME": "destination_path/FAILURE",
        }
        self.processor = Unarchiver(env=deepcopy(self.processor_env))

        self._popen_patcher = unittest.mock.patch.object(
            UnarchiverModule.subprocess, "Popen", autospec=True
        )
        self.popen_mock = self._popen_patcher.start()
        self.process_mock = self.popen_mock.return_value

        self.addCleanup(unittest.mock.patch.stopall)
        self.addCleanup(self.tempdir.cleanup)

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

        utility_cases: List[Tuple[str, str, Optional[str]]] = [
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
        native_cases: List[
            Tuple[str, UnarchiverModule.ExtractorType, Optional[str], str]
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
