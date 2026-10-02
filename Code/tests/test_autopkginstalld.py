#!/usr/local/autopkg/python
#
# Copyright 2025 Elliot Jordan
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

import plistlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests import DaemonHandlerContractTests, DaemonServerContractTests

# Only load the module on Darwin, otherwise create empty module
if sys.platform == "darwin":
    # Mock the imports before importing the module
    sys.modules["installer"] = MagicMock()
    sys.modules["itemcopier"] = MagicMock()
    sys.modules["launch2"] = MagicMock()

    # Load autopkginstalld as a module by reading and executing it
    autopkginstalld_path = (
        Path(__file__).parent.parent / "autopkgserver" / "autopkginstalld"
    )
    with open(autopkginstalld_path, "r", encoding="utf-8") as f:
        autopkginstalld_code = f.read()

    # Create a module
    autopkginstalld = types.ModuleType("autopkginstalld")
    autopkginstalld.__file__ = str(autopkginstalld_path)
    sys.modules["autopkginstalld"] = autopkginstalld

    # Execute the code in the module's namespace
    exec(autopkginstalld_code, autopkginstalld.__dict__)

    # Import what we need
    APPNAME = autopkginstalld.APPNAME
    VERSION = autopkginstalld.VERSION
    AutoPkgInstallDaemon = autopkginstalld.AutoPkgInstallDaemon
    AutoPkgInstallDaemonError = autopkginstalld.AutoPkgInstallDaemonError
    RunHandler = autopkginstalld.RunHandler
    main = autopkginstalld.main
else:
    # Create dummy objects for non-Darwin platforms
    APPNAME = "autopkginstalld"
    VERSION = "0.0.0"
    AutoPkgInstallDaemon = MagicMock
    AutoPkgInstallDaemonError = Exception
    RunHandler = MagicMock
    main = MagicMock


@unittest.skipUnless(sys.platform == "darwin", "Unix sockets are Unix-only")
class TestRunHandler(DaemonHandlerContractTests, unittest.TestCase):
    """Test class for RunHandler."""

    daemon_module = "autopkginstalld"
    outer_error_message = b"ERROR:Caught exception: RuntimeError('boom')"

    def setUp(self):
        """Set up test fixtures."""
        self.handler = RunHandler(
            request=MagicMock(), client_address=("127.0.0.1", 12345), server=MagicMock()
        )
        self.handler.log = MagicMock()

    def test_verify_request_syntax_valid_package_request(self):
        """Should return True and no errors for valid package request."""
        plist = {
            "package": "/path/to/package.pkg",
            "recipe_cache_dir": "/path/to/cache",
        }
        syntax_ok, errors = self.handler.verify_request_syntax(plist)

        self.assertTrue(syntax_ok)
        self.assertEqual(errors, [])

    def test_verify_request_syntax_invalid_mount_point_request(self):
        """Should return False when only mount_point is provided without package key."""
        plist = {"mount_point": "/Volumes/Something"}
        syntax_ok, errors = self.handler.verify_request_syntax(plist)

        # mount_point is handled separately in the handle method.
        self.assertFalse(syntax_ok)
        self.assertIn("Request does not contain package", errors[0])

    def test_verify_request_syntax_missing_package_key(self):
        """Should return False and error when package key is missing."""
        plist = {"something": "else"}
        syntax_ok, errors = self.handler.verify_request_syntax(plist)

        self.assertFalse(syntax_ok)
        self.assertEqual(len(errors), 2)
        self.assertIn("Request does not contain package", errors[0])

    def test_verify_request_syntax_missing_recipe_cache_dir_key(self):
        """Should return False and error when recipe_cache_dir is missing."""
        plist = {"package": "/path/to/package.pkg"}
        syntax_ok, errors = self.handler.verify_request_syntax(plist)

        self.assertFalse(syntax_ok)
        self.assertEqual(len(errors), 1)
        self.assertIn("Request does not contain recipe_cache_dir", errors[0])

    def _make_handler(self, plist=None):
        plist = {} if plist is None else plist
        handler = RunHandler.__new__(RunHandler)
        handler.server = types.SimpleNamespace(log=MagicMock())
        handler.request = MagicMock()
        handler.request.recv.return_value = plistlib.dumps(plist)
        handler.getpeerid = MagicMock(return_value=(501, (20,)))
        return handler

    def test_handle_dispatches_package_requests_to_installer(self):
        """Should dispatch package requests to Installer workers."""
        plist = {
            "package": "/path/to/package.pkg",
            "recipe_cache_dir": "/path/to/cache",
        }
        handler = self._make_handler(plist)

        with patch("autopkginstalld.Installer") as mock_installer:
            handler.handle()

        mock_installer.assert_called_once_with(
            handler.server.log, handler.request, plist
        )
        mock_installer.return_value.install.assert_called_once_with()
        handler.request.send.assert_called_with(b"OK:DONE\n")

    def test_handle_dispatches_mount_requests_to_itemcopier(self):
        """Should dispatch mount requests to ItemCopier workers."""
        plist = {
            "mount_point": "/private/tmp/mount",
            "items_to_copy": [
                {"source_item": "Test.app", "destination_path": "/Applications"}
            ],
        }
        handler = self._make_handler(plist)

        with patch("autopkginstalld.ItemCopier") as mock_itemcopier:
            handler.handle()

        mock_itemcopier.assert_called_once_with(
            handler.server.log, handler.request, plist
        )
        mock_itemcopier.return_value.copy.assert_called_once_with()
        handler.request.send.assert_called_with(b"OK:DONE\n")


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(sys.platform == "darwin", "Unix sockets are Unix-only")
class TestAutoPkgInstallDaemon(DaemonServerContractTests, unittest.TestCase):
    """Socket, logging, main() and constants for the autopkginstalld daemon."""

    daemon_module = "autopkginstalld"
    daemon_cls = AutoPkgInstallDaemon
    handler_cls = RunHandler
    daemon_error_cls = AutoPkgInstallDaemonError
    appname = APPNAME
    version = VERSION
    main_func = staticmethod(main)


if __name__ == "__main__":
    unittest.main()
