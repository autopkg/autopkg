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

import base64
import os
import tempfile
import unittest

from autopkglib import ProcessorError
from autopkglib.SparkleSignatureVerifier import SparkleSignatureVerifier

PUBKEY_B64 = "26hQDWNqz2Xx3V+rEsk57pgg5tlzjyApHg6u+ijGmUE="
SIG_B64 = (
    "P+IK1NlMHKTWGNRKtCMA0VVAcbY05IILV9ZzqvXIRTRVWikoImYXBnC7iPD9"
    "WmMR7FB+ry26wEJv84Y43nPGAQ=="
)
MSG = b"autopkg sparkle eddsa test vector"


class TestSparkleSignatureVerifier(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.write(MSG)
        self.tmp.flush()
        self.tmp.close()

        self.processor = SparkleSignatureVerifier()
        self.processor.env = {
            "input_path": self.tmp.name,
            "eddsa_public_key": PUBKEY_B64,
            "eddsa_signature": SIG_B64,
        }

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_valid_passes(self):
        self.processor.main()  # should not raise

    def test_tampered_file_fails(self):
        with open(self.tmp.name, "wb") as fh:
            fh.write(MSG + b"tampered")
        with self.assertRaisesRegex(ProcessorError, "verification failed"):
            self.processor.main()

    def test_missing_eddsa_signature_fails(self):
        self.processor.env["eddsa_signature"] = ""
        with self.assertRaisesRegex(ProcessorError, "No sparkle:edSignature"):
            self.processor.main()

    def test_dsa_only_marker_fails_with_specific_message(self):
        self.processor.env["eddsa_signature"] = ""
        self.processor.env["sparkle_dsa_signature_present"] = True
        with self.assertRaisesRegex(ProcessorError, "dsaSignature"):
            self.processor.main()

    def test_dsa_only_marker_with_unresolved_signature_fails_dsa_specific(self):
        """AutoPkg unresolved %eddsa_signature% should be treated as missing."""
        del self.processor.env["eddsa_signature"]
        self.processor.env["sparkle_dsa_signature_present"] = True
        self.processor.inject(
            {
                "eddsa_signature": "%eddsa_signature%",
                "sparkle_dsa_signature_present": "%sparkle_dsa_signature_present%",
            }
        )
        with self.assertRaisesRegex(ProcessorError, "dsaSignature"):
            self.processor.process()

    def test_missing_signature_with_unresolved_marker_is_not_dsa(self):
        """An unresolved optional DSA marker should be treated as absent."""
        del self.processor.env["eddsa_signature"]
        self.processor.inject(
            {
                "eddsa_signature": "%eddsa_signature%",
                "sparkle_dsa_signature_present": "%sparkle_dsa_signature_present%",
            }
        )
        with self.assertRaisesRegex(ProcessorError, "No sparkle:edSignature"):
            self.processor.process()

    def test_bad_base64_public_key_fails(self):
        self.processor.env["eddsa_public_key"] = "not-valid-base64!!!"
        with self.assertRaisesRegex(ProcessorError, "base64"):
            self.processor.main()

    def test_wrong_key_length_fails(self):
        # Valid base64 but decodes to wrong length
        self.processor.env["eddsa_public_key"] = base64.b64encode(b"tooshort").decode()
        with self.assertRaisesRegex(ProcessorError, "Malformed"):
            self.processor.main()

    def test_wrong_signature_length_fails(self):
        self.processor.env["eddsa_signature"] = base64.b64encode(b"tooshort").decode()
        with self.assertRaisesRegex(ProcessorError, "Malformed"):
            self.processor.main()

    def test_non_numeric_length_fails(self):
        self.processor.env["eddsa_signature_length"] = "notanumber"
        with self.assertRaisesRegex(ProcessorError, "file size"):
            self.processor.main()

    def test_size_mismatch_fails_before_crypto(self):
        actual = os.path.getsize(self.tmp.name)
        self.processor.env["eddsa_signature_length"] = str(actual + 1)
        with self.assertRaisesRegex(ProcessorError, "!= expected"):
            self.processor.main()

    def test_correct_length_passes(self):
        actual = os.path.getsize(self.tmp.name)
        self.processor.env["eddsa_signature_length"] = str(actual)
        self.processor.main()  # should not raise

    def test_unresolved_optional_length_is_ignored(self):
        """AutoPkg unresolved %eddsa_signature_length% should stay optional."""
        self.processor.inject({"eddsa_signature_length": "%eddsa_signature_length%"})
        self.processor.process()  # should not raise


if __name__ == "__main__":
    unittest.main()
