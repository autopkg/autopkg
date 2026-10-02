#!/usr/local/autopkg/python
#
# Copyright 2013 Greg Neagle
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

"""See docstring for PathDeleter class"""

import os
import shutil
import time

from autopkglib import Processor, ProcessorError

__all__ = ["PathDeleter"]

# Directories can briefly resist removal right after a build (for example a
# file is still held open by another process), so removal is retried a few
# times with exponential backoff before giving up.
DIR_REMOVAL_MAX_ATTEMPTS = 3
DIR_REMOVAL_INITIAL_DELAY = 1


class PathDeleter(Processor):
    """Deletes file paths."""

    description = __doc__
    lifecycle = {"introduced": "0.1.0"}
    input_variables = {
        "path_list": {
            "required": True,
            "description": (
                "An array or list of pathnames to be deleted, "
                "even if that list contains a single item."
            ),
        },
        "continue_on_error": {
            "required": False,
            "description": (
                "If True, PathDeleter will not raise a ProcessorError when a "
                "path cannot be removed: a missing path is skipped, and a "
                "directory that still cannot be removed after retrying is "
                "force-removed with errors ignored. Useful for best-effort "
                "cleanup steps (e.g. clearing a cache) that should never fail "
                "the recipe run. Defaults to False, which preserves the "
                "original behavior of raising on any failure."
            ),
            "default": False,
        },
    }
    output_variables = {}

    def _remove_directory(self, path: str, continue_on_error: bool) -> None:
        """Remove a directory tree, retrying transient failures.

        Retries shutil.rmtree with exponential backoff. Once the attempts are
        exhausted, either raise a ProcessorError (the default) or, when
        continue_on_error is True, force removal with errors ignored.
        """
        delay = DIR_REMOVAL_INITIAL_DELAY
        last_err = None
        for attempt in range(1, DIR_REMOVAL_MAX_ATTEMPTS + 1):
            try:
                shutil.rmtree(path)
                self.output(f"Deleted {path}")
                return
            except OSError as err:
                last_err = err
                if attempt < DIR_REMOVAL_MAX_ATTEMPTS:
                    self.output(
                        f"Unable to remove {path} (attempt {attempt} of "
                        f"{DIR_REMOVAL_MAX_ATTEMPTS}); retrying in {delay}s"
                    )
                    time.sleep(delay)
                    delay *= 2

        # Every attempt failed.
        if continue_on_error:
            self.output(f"Ignoring errors on final removal of {path}")
            shutil.rmtree(path, ignore_errors=True)
        else:
            raise ProcessorError(
                f"Could not remove {path} after "
                f"{DIR_REMOVAL_MAX_ATTEMPTS} attempts: {last_err}"
            ) from last_err

    def main(self) -> None:
        # if recipe writer gave us a single string instead of a list of strings,
        # convert it to a list of strings
        if isinstance(self.env["path_list"], str):
            self.env["path_list"] = [self.env["path_list"]]

        continue_on_error = self.env.get("continue_on_error", False)

        for path in self.env["path_list"]:
            try:
                if os.path.isfile(path) or os.path.islink(path):
                    os.remove(path)
                    self.output(f"Deleted {path}")
                elif os.path.isdir(path):
                    self._remove_directory(path, continue_on_error)
                elif not os.path.exists(path):
                    if continue_on_error:
                        self.output(f"Path does not exist, skipping: {path}")
                    else:
                        raise ProcessorError(
                            f"Could not remove {path} - it does not exist! "
                            "Set continue_on_error=True to skip missing paths."
                        )
                else:
                    raise ProcessorError(
                        f"Could not remove {path} - it is not a file, link, "
                        "or directory"
                    )
            except OSError as err:
                if continue_on_error:
                    self.output(f"Ignoring error removing {path}: {err}")
                else:
                    raise ProcessorError(f"Could not remove {path}: {err}") from err


if __name__ == "__main__":
    PROCESSOR = PathDeleter()
    PROCESSOR.execute_shell()
