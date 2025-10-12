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
"""
Wrapper module that provides a consistent xattr interface
regardless of platform support.
"""
from typing import Any

from autopkglib import log_err

__all__ = ["getxattr", "listxattr", "removexattr", "setxattr"]


class __xattr_wrapper:
    def __init__(self, impl: Any) -> None:
        self._impl = impl

    def getxattr(self, path: str, attr: str, symlink: bool = False) -> str:
        return self._impl.getxattr(path, attr, symlink)

    def listxattr(self, path: str, symlink: bool = False) -> list[str]:
        return self._impl.listxattr(path, symlink)

    def removexattr(self, path: str, attr: str, symlink: bool = False) -> None:
        return self._impl.removexattr(path, attr, symlink)

    def setxattr(
        self, path: str, attr: str, value: str, options: int = 0, symlink: bool = False
    ) -> None:
        return self._impl.setxattr(path, attr, value, options, symlink)


_xattr = __xattr_wrapper(None)

try:
    import xattr as _xattr_real  # type: ignore

    _xattr = __xattr_wrapper(_xattr_real)
except ImportError:
    log_err("WARNING: Library 'xattr' unavailable. Defining no-op implementation.")

    class __xattr_stub:
        """A stub class that will perform noop for any calls to the
        xattr module on platforms where it is not supported."""

        @staticmethod
        def getxattr(cls, path: str, attr: str, symlink: bool = False) -> str | None:
            return None

        @staticmethod
        def listxattr(cls, path: str, symlink: bool = False) -> list[str]:
            return []

        @staticmethod
        def removexattr(cls, path: str, attr: str, symlink: bool = False) -> None:
            return None

        @staticmethod
        def setxattr(
            cls,
            path: str,
            attr: str,
            value: str,
            options: int = 0,
            symlink: bool = False,
        ) -> None:
            return None

    _xattr = __xattr_wrapper(__xattr_stub)

assert (
    _xattr._impl is not None
), "Failed to initialize xattr library, or stub. This is a bug."


def getxattr(path: str, attr: str, symlink: bool = False) -> str | None:
    try:
        return _xattr.getxattr(path, attr, symlink)
    except OSError as e:
        log_err(f"WARNING: xattr.getxattr threw OSError. {e}")
        return None


def listxattr(path: str, symlink: bool = False) -> list[str]:
    try:
        return _xattr.listxattr(path, symlink)
    except OSError as e:
        log_err(f"WARNING: xattr.listxattr threw OSError. {e}")
        return []


def removexattr(path: str, attr: str, symlink: bool = False) -> None:
    try:
        return _xattr.removexattr(path, attr, symlink)
    except OSError as e:
        log_err(f"WARNING: xattr.removexattr threw OSError. {e}")
        return None


def setxattr(
    path: str, attr: str, value: str, options: int = 0, symlink: bool = False
) -> None:
    try:
        return _xattr.setxattr(path, attr, value, options, symlink)
    except OSError as e:
        log_err(f"WARNING: xattr.setxattr threw OSError. {e}")
        return None
