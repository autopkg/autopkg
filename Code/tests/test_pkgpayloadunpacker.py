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

import unittest
from unittest.mock import MagicMock, patch

from autopkglib import ProcessorError
from autopkglib.PkgPayloadUnpacker import PkgPayloadUnpacker


def _fake_proc(returncode, stderr=""):
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate.return_value = ("", stderr)
    return proc


class TestPkgPayloadUnpacker(unittest.TestCase):
    def setUp(self):
        self.processor = PkgPayloadUnpacker()
        self.processor.env = {
            "pkg_payload_path": "/tmp/Payload",
            "destination_path": "/tmp/dest",
        }

    def _unpack(self, procs, aa_exists=True):
        """Run unpack_pkg_payload with Popen returning each proc in turn."""
        with (
            patch(
                "os.path.exists",
                side_effect=lambda p: aa_exists if p == "/usr/bin/aa" else True,
            ),
            patch("subprocess.Popen", side_effect=procs),
            patch.object(self.processor, "output"),
        ):
            self.processor.unpack_pkg_payload()

    def test_both_extractors_failing_reports_both_errors(self):
        """The ditto diagnostic must survive the aa fallback also failing —
        otherwise the more informative of the two errors is discarded."""
        with self.assertRaises(ProcessorError) as err:
            self._unpack(
                [
                    _fake_proc(1, "ditto: Invalid argument"),
                    _fake_proc(1, "aa: unrecognized archive"),
                ]
            )

        message = str(err.exception)
        self.assertIn("ditto: Invalid argument", message)
        self.assertIn("aa: unrecognized archive", message)

    def test_ditto_failure_alone_is_reported_when_aa_is_absent(self):
        with self.assertRaises(ProcessorError) as err:
            self._unpack([_fake_proc(1, "ditto: Invalid argument")], aa_exists=False)

        self.assertIn("ditto: Invalid argument", str(err.exception))

    def test_aa_success_clears_the_ditto_error(self):
        """A successful fallback must not surface ditto's failure as an error."""
        self._unpack([_fake_proc(1, "ditto: Invalid argument"), _fake_proc(0)])

    def test_unrunnable_ditto_does_not_raise_unbound_local_error(self):
        """When ditto can't be executed at all there is no proc to inspect."""
        with (
            patch("os.path.exists", return_value=False),
            # exists() False sends the processor down the mkdir path; don't let
            # it touch the real filesystem.
            patch("os.makedirs"),
            patch("subprocess.Popen", side_effect=OSError(2, "No such file")),
            patch.object(self.processor, "output"),
        ):
            with self.assertRaises(ProcessorError) as err:
                self.processor.unpack_pkg_payload()

        self.assertIn("ditto execution failed", str(err.exception))


if __name__ == "__main__":
    unittest.main()
