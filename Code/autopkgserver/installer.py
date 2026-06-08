# Copyright 2014 Greg Neagle
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

"""Runs installer to install a package. Can install a package located inside a
disk image file."""

import os
import subprocess

PRIVATE_TMP = "/private/tmp"


class InstallerError(Exception):
    """Base error for Installer errors"""

    pass


def is_path_under(path, root):
    """Return True if path is at or below root."""
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:
        return False


def path_has_mountpoint_under(path, root):
    """Return True if path is within a mounted volume under root."""
    root = os.path.realpath(root)
    path = os.path.realpath(path)
    if not is_path_under(path, root):
        return False

    check_path = path if os.path.isdir(path) else os.path.dirname(path)
    while is_path_under(check_path, root):
        if check_path != root and os.path.ismount(check_path):
            return True
        parent_path = os.path.dirname(check_path)
        if parent_path == check_path:
            break
        check_path = parent_path
    return False


class Installer:
    """Runs /usr/sbin/installer to install a package"""

    def __init__(self, log, socket, request):
        """Arguments:

        log     A logger instance.
        socket  The socket for the requesting object
        request A request in plist format.
        """

        self.log = log
        self.socket = socket
        self.request = request
        self.package_path: str | None = None

    def allowed_package_roots(self):
        """Return roots from which package paths may be installed."""
        return (
            os.path.realpath(self.request["recipe_cache_dir"]),
            os.path.realpath(PRIVATE_TMP),
        )

    def package_path_is_allowed(self, package_path):
        """Return True if package_path is in the recipe cache or a temp mount."""
        cache_root, tmp_root = self.allowed_package_roots()
        if is_path_under(package_path, cache_root):
            return True
        return path_has_mountpoint_under(package_path, tmp_root)

    def verify_request(self) -> None:
        """Make sure copy request has everything we need"""
        self.log.debug("Verifying install request")
        for key in ["package", "recipe_cache_dir"]:
            if key not in self.request:
                raise InstallerError(f"ERROR:No {key} in request")
        if not isinstance(self.request["package"], str) or not self.request["package"]:
            raise InstallerError("Package path is required")
        if (
            not isinstance(self.request["recipe_cache_dir"], str)
            or not self.request["recipe_cache_dir"]
        ):
            raise InstallerError("Recipe cache directory is required")

        package_path = os.path.realpath(self.request["package"])
        if not self.package_path_is_allowed(package_path):
            raise InstallerError(
                f"Package path {self.request['package']} is not in an allowed location"
            )
        if not os.path.exists(package_path):
            raise InstallerError(
                f"Package path {self.request['package']} does not exist"
            )
        self.package_path = package_path

    def do_install(self) -> bool:
        """Call /usr/sbin/installer"""
        pkg_path = self.package_path
        if pkg_path is None:
            raise InstallerError("Package path is required")
        try:
            cmd = ["/usr/sbin/installer", "-verboseR", "-pkg", pkg_path, "-target", "/"]
            proc = subprocess.Popen(
                cmd,
                shell=False,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            if proc.stdout is None:
                raise InstallerError("Installer output stream is unavailable")
            while True:
                output = proc.stdout.readline()
                if not output and (proc.poll() is not None):
                    break
                if output:
                    self.socket.send(f"STATUS:{output}".encode())
                    self.log.info(output.rstrip())

            if proc.returncode != 0:
                raise InstallerError(f"ERROR:{proc.returncode}\n")
            self.log.info("install request completed.")
            return True
        except Exception as err:
            self.log.error("Install failed: %s", err)
            raise InstallerError(f"ERROR:{err}\n")

    def install(self) -> None:
        """Main method."""
        try:
            self.verify_request()
            self.do_install()
        except Exception as err:
            raise InstallerError(err)
