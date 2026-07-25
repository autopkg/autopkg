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

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from autopkglib import ProcessorError
from autopkglib.Installer import Installer


class TestInstaller(unittest.TestCase):
    """Test class for Installer processor."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.recipe_cache_dir = os.path.join(self.tmp_dir.name, "recipe-cache")
        os.makedirs(self.recipe_cache_dir)
        self.package_path = os.path.join(self.recipe_cache_dir, "Test.pkg")
        Path(self.package_path).touch()
        self.processor = Installer()
        self.processor.env = {
            "pkg_path": self.package_path,
            "RECIPE_CACHE_DIR": self.recipe_cache_dir,
        }

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_install_request_includes_recipe_cache_dir(self):
        """Should send the effective recipe cache directory to the daemon."""
        with (
            patch.object(self.processor, "connect") as mock_connect,
            patch.object(
                self.processor, "send_request", return_value="DONE"
            ) as mock_send_request,
            patch.object(self.processor, "disconnect") as mock_disconnect,
        ):
            self.processor.install()

        mock_connect.assert_called_once_with()
        mock_send_request.assert_called_once_with(
            {
                "package": self.package_path,
                "recipe_cache_dir": self.recipe_cache_dir,
            }
        )
        mock_disconnect.assert_called_once_with()

    def test_send_request_empty_reply(self):
        """An empty reply should report that autopkginstalld sent no reply."""
        mock_file = MagicMock()
        mock_file.readline.return_value = ""
        self.processor.socket = MagicMock()

        with (
            # Patch os directly: autopkglib.Installer resolves to the Installer
            # class, not the module, so a module-scoped target fails on 3.10.
            patch("os.fdopen") as mock_fdopen,
            patch("plistlib.dumps", return_value=b""),
        ):
            mock_fdopen.return_value.__enter__.return_value = mock_file
            with self.assertRaisesRegex(
                ProcessorError, "No reply from autopkginstalld"
            ):
                self.processor.send_request({"package": self.package_path})


if __name__ == "__main__":
    unittest.main()
