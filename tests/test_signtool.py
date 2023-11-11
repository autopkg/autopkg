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

import sys
import unittest
from typing import Any, Dict

from autopkg.autopkglib.SignToolVerifier import ProcessorError, SignToolVerifier


class TestSignToolVerifier(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32", "Requires Windows")
    def test_verify_ntdll(self):
        env: Dict[str, str] = {"input_path": r"C:\Windows\System32\ntdll.dll"}
        processor = SignToolVerifier(env)
        processor.process()

    @unittest.skipUnless(sys.platform == "win32", "Requires Windows")
    def test_verify_nopath(self):
        env: Dict[str, Any] = {"input_path": r"C:\Fake\Path\To.dll", "verbose": 4}
        processor = SignToolVerifier(env)
        self.assertRaises(ProcessorError, processor.process)


if __name__ == "__main__":
    unittest.main()
