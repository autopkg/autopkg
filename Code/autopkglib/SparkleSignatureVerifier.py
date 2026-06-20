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

"""See docstring for SparkleSignatureVerifier class"""

import base64
import os
import re

from autopkglib import Processor, ProcessorError
from autopkglib.crypto import ed25519

__all__ = ["SparkleSignatureVerifier"]

_UNRESOLVED_KEYREF = re.compile(r"^%[a-zA-Z_][a-zA-Z_0-9]*%$")


def _clean_input(value):
    """Normalize absent AutoPkg substitutions to None."""
    if isinstance(value, str):
        value = value.strip()
        if _UNRESOLVED_KEYREF.fullmatch(value):
            return None
    return value


def _truthy_marker(value):
    """Return True only for explicit truthy marker values."""
    value = _clean_input(value)
    if isinstance(value, str):
        return value.lower() in ("1", "true", "yes")
    return bool(value)


class SparkleSignatureVerifier(Processor):
    """Verifies a Sparkle EdDSA (Ed25519) signature for a downloaded archive.

    Requires a pinned SUPublicEDKey from the vendor's app Info.plist and the
    sparkle:edSignature from the appcast (typically via SparkleUpdateInfoProvider).
    Fails closed: any missing or invalid input raises ProcessorError.
    """

    description = __doc__
    lifecycle = {"introduced": "3.1.0"}
    input_variables = {
        "input_path": {
            "required": True,
            "description": "Path to the downloaded archive to verify.",
        },
        "eddsa_public_key": {
            "required": True,
            "description": "Pinned base64-encoded SUPublicEDKey from the vendor.",
        },
        "eddsa_signature": {
            "required": True,
            "description": "Base64 sparkle:edSignature from the appcast.",
        },
        "eddsa_signature_length": {
            "required": False,
            "description": "Expected file size from the enclosure length attribute.",
        },
        "sparkle_dsa_signature_present": {
            "required": False,
            "description": "Set by SparkleUpdateInfoProvider for DSA-only appcast items.",
        },
    }
    output_variables = {}

    def main(self):
        sig_b64 = _clean_input(self.env.get("eddsa_signature"))
        if not sig_b64:
            if _truthy_marker(self.env.get("sparkle_dsa_signature_present")):
                raise ProcessorError(
                    "Selected appcast item has legacy sparkle:dsaSignature but no "
                    "sparkle:edSignature. DSA verification is not supported."
                )
            raise ProcessorError(
                "No sparkle:edSignature provided; refusing to proceed."
            )

        try:
            public_key = base64.b64decode(self.env["eddsa_public_key"], validate=True)
            signature = base64.b64decode(sig_b64, validate=True)
        except Exception as err:
            raise ProcessorError(
                f"Could not base64-decode EdDSA key or signature: {err}"
            ) from err

        path = self.env["input_path"]
        expected = _clean_input(self.env.get("eddsa_signature_length"))
        if expected is not None:
            try:
                expected_size = int(expected)
                actual_size = os.path.getsize(path)
            except (OSError, TypeError, ValueError) as err:
                raise ProcessorError(
                    f"Could not validate expected file size: {err}"
                ) from err
            if actual_size != expected_size:
                raise ProcessorError(
                    f"File size {actual_size} != expected {expected_size}."
                )

        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError as err:
            raise ProcessorError(f"Could not read {path}: {err}") from err

        try:
            verified = ed25519.verify(public_key, signature, data)
        except ValueError as err:
            raise ProcessorError(f"Malformed EdDSA key or signature: {err}") from err

        if not verified:
            raise ProcessorError(f"EdDSA signature verification failed for {path}.")

        self.output("EdDSA signature verified against pinned public key.")


if __name__ == "__main__":
    PROCESSOR = SparkleSignatureVerifier()
    PROCESSOR.execute_shell()
