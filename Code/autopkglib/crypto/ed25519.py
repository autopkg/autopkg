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

"""Ed25519 verify-only helper (RFC 8032). No signing, no key generation."""

import hashlib

# Field prime and group order for Ed25519
_P = 2**255 - 19
_L = 2**252 + 27742317777372353535851937790883648493

# Curve constant d = -121665/121666 mod p
_D = -121665 * pow(121666, _P - 2, _P) % _P

# sqrt(-1) mod p, needed for point decompression
_SQRT_M1 = pow(2, (_P - 1) // 4, _P)

# Base point y-coordinate: 4/5 mod p
_GY = 4 * pow(5, _P - 2, _P) % _P


def _recover_x(y, sign):
    """Recover x from a compressed y and sign bit. Returns None for invalid points."""
    if y >= _P:
        return None
    x2 = (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P) % _P
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_P + 3) // 8, _P)
    if x * x % _P != x2:
        x = x * _SQRT_M1 % _P
    if x * x % _P != x2:
        return None
    if x & 1 != sign:
        x = _P - x
    return x


# Base point in extended coordinates (X, Y, Z, T) where x=X/Z, y=Y/Z, T=X*Y/Z
_GX = _recover_x(_GY, 0)
_G = (_GX, _GY, 1, _GX * _GY % _P)

_IDENTITY_BYTES = (1).to_bytes(32, "little")


def _add(P, Q):
    """Unified twisted Edwards addition in extended coordinates."""
    A = (P[1] - P[0]) * (Q[1] - Q[0]) % _P
    B = (P[1] + P[0]) * (Q[1] + Q[0]) % _P
    C = 2 * P[3] * Q[3] * _D % _P
    D = 2 * P[2] * Q[2] % _P
    E, F, G_, H = B - A, D - C, D + C, B + A
    return E * F % _P, H * G_ % _P, F * G_ % _P, E * H % _P


def _mul(s, P):
    """Scalar multiplication via double-and-add."""
    Q = (0, 1, 1, 0)  # neutral element
    while s:
        if s & 1:
            Q = _add(Q, P)
        P = _add(P, P)
        s >>= 1
    return Q


def _compress(P):
    """Compress an extended-coordinate point to 32 bytes."""
    zi = pow(P[2], _P - 2, _P)
    x, y = P[0] * zi % _P, P[1] * zi % _P
    return (y | ((x & 1) << 255)).to_bytes(32, "little")


def _decompress(b):
    """Decompress 32 bytes to extended-coordinate point, or None if invalid."""
    y = int.from_bytes(b, "little")
    sign = y >> 255
    y &= ~(1 << 255)
    x = _recover_x(y, sign)
    return None if x is None else (x, y, 1, x * y % _P)


def _is_low_order(P):
    """Return True for small-subgroup points."""
    return _compress(_mul(8, P)) == _IDENTITY_BYTES


def verify(public_key: bytes, signature: bytes, message: bytes) -> bool:
    """Verify an Ed25519 signature against a public key and message.

    Raises ValueError for wrong key or signature byte lengths.
    Returns False for any invalid signature, including non-canonical S >= L
    and invalid curve point encodings.
    """
    if len(public_key) != 32:
        raise ValueError(f"public key must be 32 bytes, got {len(public_key)}")
    if len(signature) != 64:
        raise ValueError(f"signature must be 64 bytes, got {len(signature)}")

    A = _decompress(public_key)
    if A is None or _is_low_order(A):
        return False

    R_bytes = signature[:32]
    S = int.from_bytes(signature[32:], "little")
    if S >= _L:  # non-canonical signature
        return False

    R = _decompress(R_bytes)
    if R is None or _is_low_order(R):
        return False

    h = (
        int.from_bytes(
            hashlib.sha512(R_bytes + public_key + message).digest(), "little"
        )
        % _L
    )

    # Cofactor form avoids small-subgroup contributions: [8][S]B == [8]R + [8][h]A
    lhs = _compress(_mul(8 * S, _G))
    rhs = _compress(_add(_mul(8, R), _mul(8 * h, A)))
    return lhs == rhs
