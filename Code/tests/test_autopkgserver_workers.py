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

import importlib.util
import os
import sys
import types
import unittest
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

try:
    import xattr  # noqa: F401
except ImportError:
    xattr_module = types.ModuleType("xattr")

    class FakeXattr:
        def __init__(self, path):
            self.path = path

        def list(self):
            return []

        def remove(self, name):
            pass

    xattr_module.xattr = FakeXattr
    sys.modules["xattr"] = xattr_module

AUTOPKGSERVER_DIR = Path(__file__).parent.parent / "autopkgserver"


def load_worker_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


installer = load_worker_module(
    "autopkgserver_installer_worker", AUTOPKGSERVER_DIR / "installer.py"
)
itemcopier = load_worker_module(
    "autopkgserver_itemcopier_worker", AUTOPKGSERVER_DIR / "itemcopier.py"
)


class TestInstallerValidation(unittest.TestCase):
    """Test class for Installer request validation."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.recipe_cache = os.path.join(self.tmp_dir.name, "cache", "com.test.pkg")
        os.makedirs(self.recipe_cache)
        self.private_tmp = os.path.join(self.tmp_dir.name, "private_tmp")
        os.makedirs(self.private_tmp)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _installer(self, package_path, recipe_cache_dir=None):
        request = {
            "package": package_path,
            "recipe_cache_dir": recipe_cache_dir or self.recipe_cache,
        }
        return installer.Installer(MagicMock(), MagicMock(), request)

    def test_accepts_package_in_recipe_cache(self):
        """Should accept a package under the effective recipe cache."""
        package_path = os.path.join(self.recipe_cache, "Test.pkg")
        Path(package_path).touch()

        worker = self._installer(package_path)
        worker.verify_request()

        self.assertEqual(worker.package_path, os.path.realpath(package_path))

    def test_accepts_package_in_private_tmp(self):
        """Should accept a package under the private temporary mount root."""
        mountpoint = os.path.join(self.private_tmp, "mount")
        os.makedirs(mountpoint)
        package_path = os.path.join(mountpoint, "Test.pkg")
        Path(package_path).touch()

        with (
            patch.object(installer, "PRIVATE_TMP", self.private_tmp),
            patch.object(
                installer.os.path,
                "ismount",
                side_effect=lambda path: os.path.realpath(path)
                == os.path.realpath(mountpoint),
            ),
        ):
            worker = self._installer(package_path)
            worker.verify_request()

        self.assertEqual(worker.package_path, os.path.realpath(package_path))

    def test_rejects_package_in_loose_private_tmp_path(self):
        """Should reject private temporary paths that are not in a mount."""
        package_path = os.path.join(self.private_tmp, "Test.pkg")
        Path(package_path).touch()

        with (
            patch.object(installer, "PRIVATE_TMP", self.private_tmp),
            patch.object(installer.os.path, "ismount", return_value=False),
        ):
            worker = self._installer(package_path)
            with self.assertRaises(installer.InstallerError):
                worker.verify_request()

    def test_rejects_package_outside_allowed_roots(self):
        """Should reject a package outside the request user's allowed roots."""
        package_path = os.path.join(self.tmp_dir.name, "elsewhere", "Test.pkg")
        os.makedirs(os.path.dirname(package_path))
        Path(package_path).touch()

        with (patch.object(installer, "PRIVATE_TMP", self.private_tmp),):
            worker = self._installer(package_path)
            with self.assertRaises(installer.InstallerError):
                worker.verify_request()

    def test_rejects_package_symlink_escape_from_cache(self):
        """Should reject cache packages that resolve outside the cache."""
        package_path = os.path.join(self.tmp_dir.name, "elsewhere", "Test.pkg")
        os.makedirs(os.path.dirname(package_path))
        Path(package_path).touch()
        symlink_path = os.path.join(self.recipe_cache, "Linked.pkg")
        os.symlink(package_path, symlink_path)

        worker = self._installer(symlink_path)
        with self.assertRaises(installer.InstallerError):
            worker.verify_request()

    def test_rejects_missing_recipe_cache_dir(self):
        """Should require the effective recipe cache directory."""
        package_path = os.path.join(self.recipe_cache, "Test.pkg")
        Path(package_path).touch()
        request = {"package": package_path}
        worker = installer.Installer(MagicMock(), MagicMock(), request)

        with self.assertRaises(installer.InstallerError):
            worker.verify_request()


class TestItemCopierValidation(unittest.TestCase):
    """Test class for ItemCopier request validation."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.home = os.path.join(self.tmp_dir.name, "home")
        self.cache = os.path.join(self.home, "Library", "AutoPkg", "Cache")
        os.makedirs(self.cache)
        self.private_tmp = os.path.join(self.tmp_dir.name, "private_tmp")
        self.mountpoint = os.path.join(self.private_tmp, "mount")
        os.makedirs(self.mountpoint)
        Path(os.path.join(self.mountpoint, "Test.app")).touch()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _request(self, **item_overrides):
        item = {
            "source_item": "Test.app",
            "destination_path": os.path.join(self.cache, "installed"),
        }
        item.update(item_overrides)
        return {"mount_point": self.mountpoint, "items_to_copy": [item]}

    def _copier(self, request):
        return itemcopier.ItemCopier(MagicMock(), MagicMock(), request)

    @contextmanager
    def _patched_environment(self, mounted=True):
        with (
            patch.object(itemcopier, "PRIVATE_TMP", self.private_tmp),
            patch.object(
                itemcopier.os.path,
                "ismount",
                side_effect=lambda path: mounted
                and os.path.realpath(path) == os.path.realpath(self.mountpoint),
            ),
        ):
            yield

    def test_accepts_confined_paths_and_safe_mode(self):
        """Should accept confined source paths and safe modes."""
        with self._patched_environment():
            worker = self._copier(self._request(mode="0755"))
            worker.verify_request()

        self.assertEqual(worker.mountpoint, os.path.realpath(self.mountpoint))

    def test_accepts_arbitrary_absolute_destination(self):
        """Should let trusted recipes choose an absolute destination."""
        destination_path = "/Library/Application Support/Test"
        with self._patched_environment():
            worker = self._copier(self._request(destination_path=destination_path))
            worker.verify_request()

    def test_rejects_unmounted_mount_point(self):
        """Should reject source roots that are not mounted volumes."""
        with self._patched_environment(mounted=False):
            worker = self._copier(self._request())
            with self.assertRaises(itemcopier.ItemCopierError):
                worker.verify_request()

    def test_rejects_mount_point_outside_private_tmp(self):
        """Should reject mount points outside the private temporary root."""
        outside_mount = os.path.join(self.tmp_dir.name, "outside_mount")
        os.makedirs(outside_mount)
        request = self._request()
        request["mount_point"] = outside_mount

        with self._patched_environment():
            worker = self._copier(request)
            with self.assertRaises(itemcopier.ItemCopierError):
                worker.verify_request()

    def test_rejects_source_parent_reference(self):
        """Should reject source paths with parent-directory references."""
        with self._patched_environment():
            worker = self._copier(self._request(source_item="../Test.app"))
            with self.assertRaises(itemcopier.ItemCopierError):
                worker.verify_request()

    def test_rejects_source_symlink_escape(self):
        """Should reject source symlinks that resolve outside the mount point."""
        outside_path = os.path.join(self.tmp_dir.name, "outside")
        Path(outside_path).touch()
        os.symlink(outside_path, os.path.join(self.mountpoint, "Linked.app"))

        with self._patched_environment():
            worker = self._copier(self._request(source_item="Linked.app"))
            with self.assertRaises(itemcopier.ItemCopierError):
                worker.verify_request()

    def test_rejects_destination_parent_reference(self):
        """Should reject destination paths with parent-directory references."""
        destination_path = os.path.join(self.cache, "..", "installed")
        with self._patched_environment():
            worker = self._copier(self._request(destination_path=destination_path))
            with self.assertRaises(itemcopier.ItemCopierError):
                worker.verify_request()

    def test_rejects_destination_item_parent_reference(self):
        """Should reject destination item paths with parent-directory references."""
        with self._patched_environment():
            worker = self._copier(self._request(destination_item="../Test.app"))
            with self.assertRaises(itemcopier.ItemCopierError):
                worker.verify_request()

    def test_rejects_relative_destination(self):
        """Should reject relative destination paths."""
        with self._patched_environment():
            worker = self._copier(self._request(destination_path="Applications"))
            with self.assertRaises(itemcopier.ItemCopierError):
                worker.verify_request()

    def test_rejects_setuid_and_setgid_modes(self):
        """Should reject modes that set setuid or setgid bits."""
        worker = self._copier(self._request())

        for mode in ("4755", "04755", "2755", "02755", "u+s", "g+rwxs", "a=rwxs"):
            with self.subTest(mode=mode):
                with self.assertRaises(itemcopier.ItemCopierError):
                    worker.verify_mode(mode)

    def test_accepts_safe_modes(self):
        """Should accept modes that do not set setuid or setgid bits."""
        worker = self._copier(self._request())

        for mode in ("0755", "755", "o-w", "u-s", "u=rwX,go=rX"):
            with self.subTest(mode=mode):
                worker.verify_mode(mode)


if __name__ == "__main__":
    unittest.main()
