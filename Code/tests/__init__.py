#!/usr/local/autopkg/python
#
# Copyright 2019 Nick McSpadden
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

import importlib
import importlib.machinery
import importlib.util
import os
import shutil
import sys
import tempfile
from types import ModuleType
from unittest.mock import MagicMock, patch

import autopkglib
from autopkglib import Processor


def get_processor_module(
    processor: str | type[Processor], package_name: str = "autopkglib"
) -> ModuleType:
    """Get the module for a processor, which may be passed as a string or class object.

    Typically used for patching module scoped functions for unit testing like so:
        proc_module = get_processor_module("Unarchiver")
        patcher = unittest.mock.patch.object(proc_module, "is_mac", return_value=False)

    Necessary because `autopkglib` contains code that makes it impossible to import a
    processor *module* without significant effort and/or modifications to some of the
    basic machinery of `autopkglib`. This function wraps simple `importlib` machinery.
    """
    if isinstance(processor, str):
        module_name: str = ".".join([package_name, processor])
    else:
        module_name = processor.__module__
    # The default value for `package_name` relies on the convention in
    # `autopkglib.import_processors` that expects module name to equal processor name.
    return importlib.import_module(module_name)


def load_autopkg_module() -> ModuleType:
    """Load the `autopkg` CLI script as an importable module.

    The script has no `.py` extension, so a normal import won't find it.
    The result is cached in `sys.modules` so every caller shares one module
    object: tests patch attributes on it, and `autopkg` imports names like
    `globalRecipeMap` from `autopkglib` at load time, so a second load would
    leave some callers holding a different module with stale references.
    """
    cached = sys.modules.get("autopkg")
    if cached is not None:
        return cached

    autopkg_path = os.path.join(os.path.dirname(__file__), "..", "autopkg")
    loader = importlib.machinery.SourceFileLoader("autopkg", autopkg_path)
    spec = importlib.util.spec_from_loader("autopkg", loader)
    module = importlib.util.module_from_spec(spec)
    # Register before exec so a circular import resolves to the partial module
    # rather than triggering a second load.
    sys.modules["autopkg"] = module
    loader.exec_module(module)
    return module


class RecipeMapIsolation:
    """Mixin that isolates recipe-map state between tests.

    Redirects `DEFAULT_RECIPE_MAP` to a per-test tempdir so tests never touch
    the developer's real `~/Library/AutoPkg`, resets `globalRecipeMap`, and
    clears the module-level latches that otherwise let one test's write
    failure or map miss silently change what a later test exercises.

    Use as `class TestFoo(RecipeMapIsolation, unittest.TestCase)`. Subclasses
    that define their own `setUp`/`tearDown` must call `super()`.
    """

    def setUp(self):
        super().setUp()
        self.tmpdir = tempfile.mkdtemp(prefix="autopkg_recipe_map_")
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)

        # Copy the sub-dicts, not just the outer dict. setUp clears them in
        # place below, which would empty the saved copy too if it shared them.
        self._saved_map = {
            key: dict(value) if isinstance(value, dict) else value
            for key, value in autopkglib.globalRecipeMap.items()
        }
        self._saved_default = autopkglib.DEFAULT_RECIPE_MAP
        self._saved_write_disabled = autopkglib._recipe_map_write_disabled
        self._saved_cwd_rebuild = autopkglib._recipe_map_cwd_rebuild_attempted

        autopkglib.DEFAULT_RECIPE_MAP = os.path.join(self.tmpdir, "recipe_map.json")
        autopkglib._recipe_map_write_disabled = False
        autopkglib._recipe_map_cwd_rebuild_attempted = False

        # Clear the sub-dicts in place: `globalRecipeMap` must keep object
        # identity so `from autopkglib import globalRecipeMap` importers
        # always see the live dict.
        for sub in ("identifiers", "shortnames", "overrides", "overrides-identifiers"):
            autopkglib.globalRecipeMap.setdefault(sub, {}).clear()

    def tearDown(self):
        autopkglib.globalRecipeMap.clear()
        autopkglib.globalRecipeMap.update(self._saved_map)
        autopkglib.DEFAULT_RECIPE_MAP = self._saved_default
        autopkglib._recipe_map_write_disabled = self._saved_write_disabled
        autopkglib._recipe_map_cwd_rebuild_attempted = self._saved_cwd_rebuild
        super().tearDown()


class DaemonHandlerContractTests:
    """Request-handler behaviour shared by the autopkgserver and
    autopkginstalld daemons, whose handlers are near-copies of each other.

    Subclasses must set `daemon_module` (the module name used to build patch
    targets) and `outer_error_message` (the two daemons format the caught
    exception differently), and implement `_make_handler()`.
    """

    daemon_module = ""
    outer_error_message = b""

    def _make_handler(self):
        raise NotImplementedError

    def test_verify_request_syntax_not_a_dict(self):
        """Should return False and error when plist is not a dictionary."""
        syntax_ok, errors = self.handler.verify_request_syntax(["not", "a", "dict"])

        self.assertFalse(syntax_ok)
        self.assertEqual(len(errors), 1)
        self.assertIn("Request root is not a dictionary", errors[0])

    def test_handle_reports_malformed_request_for_parse_error(self):
        """Should report malformed requests for ordinary parse errors."""
        handler = self._make_handler()

        with patch(f"{self.daemon_module}.plistlib.loads", side_effect=ValueError):
            handler.handle()

        handler.request.send.assert_called_once_with(b"ERROR:Malformed request\n")

    def test_handle_parse_does_not_wrap_keyboard_interrupt(self):
        """Should let process termination exceptions propagate."""
        handler = self._make_handler()

        with (
            patch(
                f"{self.daemon_module}.plistlib.loads", side_effect=KeyboardInterrupt
            ),
            self.assertRaises(KeyboardInterrupt),
        ):
            handler.handle()

    def test_handle_reports_ordinary_outer_errors(self):
        """Should report ordinary unexpected request handling errors."""
        handler = self._make_handler()
        handler.getpeerid.side_effect = RuntimeError("boom")

        handler.handle()

        handler.request.send.assert_called_once_with(self.outer_error_message)

    def test_handle_outer_error_does_not_wrap_keyboard_interrupt(self):
        """Should let process termination exceptions propagate."""
        handler = self._make_handler()
        handler.getpeerid.side_effect = KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            handler.handle()


class DaemonServerContractTests:
    """Socket, logging, main() and constant behaviour shared by the
    autopkgserver and autopkginstalld daemons.

    Subclasses must set `daemon_module`, `daemon_cls`, `handler_cls`,
    `daemon_error_cls`, `appname`, `version`, and `main_func` (wrap the
    function in `staticmethod` so attribute access doesn't bind it).
    """

    daemon_module = ""
    daemon_cls = None
    handler_cls = None
    daemon_error_cls = None
    appname = ""
    version = ""
    main_func = None

    def _make_daemon(self, mock_fromfd):
        mock_socket = MagicMock()
        mock_fromfd.return_value = mock_socket
        daemon = self.daemon_cls(socket_fd=3, RequestHandlerClass=self.handler_cls)
        return daemon, mock_socket

    def test_init_creates_socket(self):
        """Should create socket from file descriptor."""
        with patch(f"{self.daemon_module}.socket.fromfd") as mock_fromfd:
            daemon, mock_socket = self._make_daemon(mock_fromfd)

            mock_fromfd.assert_called_once()
            mock_socket.listen.assert_called_once_with(daemon.request_queue_size)
            self.assertFalse(daemon.timed_out)

    def test_handle_timeout_sets_flag(self):
        """Should set timed_out flag when handle_timeout is called."""
        with patch(f"{self.daemon_module}.socket.fromfd") as mock_fromfd:
            daemon, _ = self._make_daemon(mock_fromfd)
            self.assertFalse(daemon.timed_out)

            daemon.handle_timeout()
            self.assertTrue(daemon.timed_out)

    def test_setup_logging_success(self):
        """Should set up logging handlers successfully."""
        with (
            patch(f"{self.daemon_module}.socket.fromfd") as mock_fromfd,
            patch(f"{self.daemon_module}.logging.getLogger") as mock_get_logger,
            patch(f"{self.daemon_module}.logging.StreamHandler"),
            patch(f"{self.daemon_module}.logging.handlers.RotatingFileHandler"),
        ):
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            daemon, _ = self._make_daemon(mock_fromfd)
            daemon.setup_logging()

            mock_get_logger.assert_called_once_with(self.appname)
            mock_logger.setLevel.assert_called_once()
            self.assertEqual(mock_logger.addHandler.call_count, 2)

    def test_setup_logging_raises_on_file_error(self):
        """Should raise the daemon's error type when file logging fails."""
        with (
            patch(f"{self.daemon_module}.socket.fromfd") as mock_fromfd,
            patch(f"{self.daemon_module}.logging.getLogger") as mock_get_logger,
            patch(
                f"{self.daemon_module}.logging.handlers.RotatingFileHandler"
            ) as mock_file_handler,
        ):
            mock_get_logger.return_value = MagicMock()
            mock_file_handler.side_effect = OSError(13, "Permission denied")

            daemon, _ = self._make_daemon(mock_fromfd)

            with self.assertRaises(self.daemon_error_cls) as ctx:
                daemon.setup_logging()

            self.assertIn("Can't open log", str(ctx.exception))

    def test_main_requires_root(self):
        """Should return 1 if not running as root."""
        with (
            patch(f"{self.daemon_module}.os.geteuid", return_value=501),
            patch(f"{self.daemon_module}.time.sleep"),
        ):
            self.assertEqual(self.main_func([]), 1)

    def test_appname_constant(self):
        """APPNAME should be set correctly."""
        self.assertEqual(self.appname, self.daemon_module)

    def test_version_constant(self):
        """VERSION should be set and be a valid version string."""
        self.assertIsInstance(self.version, str)
        self.assertRegex(self.version, r"^\d+\.\d+")
