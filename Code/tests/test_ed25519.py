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
import unittest

from autopkglib.crypto import ed25519

# Test vectors generated against the Sparkle EdDSA implementation.
PUBKEY_B64 = "26hQDWNqz2Xx3V+rEsk57pgg5tlzjyApHg6u+ijGmUE="
SIG_B64 = (
    "P+IK1NlMHKTWGNRKtCMA0VVAcbY05IILV9ZzqvXIRTRVWikoImYXBnC7iPD9"
    "WmMR7FB+ry26wEJv84Y43nPGAQ=="
)
# Same signature with S replaced by S + L (non-canonical)
NC_SIG_B64 = (
    "P+IK1NlMHKTWGNRKtCMA0VVAcbY05IILV9ZzqvXIRTRCLh+FPMkpXkZYgJPc"
    "VEIm7FB+ry26wEJv84Y43nPGEQ=="
)
MSG = b"autopkg sparkle eddsa test vector"


class TestEd25519Verify(unittest.TestCase):
    def setUp(self):
        self.pk = base64.b64decode(PUBKEY_B64)
        self.sig = base64.b64decode(SIG_B64)

    def test_valid_signature(self):
        self.assertTrue(ed25519.verify(self.pk, self.sig, MSG))

    def test_tampered_message(self):
        self.assertFalse(ed25519.verify(self.pk, self.sig, MSG + b"!"))

    def test_wrong_key(self):
        # A point that does not decompress to a valid curve point
        bad_key = bytes([0xFF] * 32)
        self.assertFalse(ed25519.verify(bad_key, self.sig, MSG))

    def test_low_order_key_and_r_are_rejected(self):
        identity = (1).to_bytes(32, "little")
        zero_sig = identity + bytes(32)
        self.assertFalse(ed25519.verify(identity, zero_sig, MSG))

    def test_non_canonical_signature(self):
        # S + L is congruent mod L but must be rejected
        nc_sig = base64.b64decode(NC_SIG_B64)
        self.assertFalse(ed25519.verify(self.pk, nc_sig, MSG))

    def test_wrong_key_length_raises(self):
        with self.assertRaises(ValueError):
            ed25519.verify(b"short", self.sig, MSG)

    def test_wrong_signature_length_raises(self):
        with self.assertRaises(ValueError):
            ed25519.verify(self.pk, b"short", MSG)


if __name__ == "__main__":
    unittest.main()
