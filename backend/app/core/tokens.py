"""Opaque tokens for email verification and password reset.

These are **not** JWTs, and the difference is the point:

* A JWT is *signed*. Its contents can be read by anyone holding it, and it
  cannot be revoked before it expires.
* An opaque token is random. It carries no information, it is stored hashed,
  and it can be invalidated the instant it is used.

A password-reset link is a bearer credential for the account. It should be
readable only by the person it was sent to, and it should stop working the
moment it is used. Neither property is available from a signed token.

The token is 32 bytes of ``secrets`` output — 43 characters of URL-safe
base64 — and only its SHA-256 digest is stored. A database leak therefore
does not hand out working reset links.
"""

from __future__ import annotations

import hashlib
import secrets

#: The number of random bytes in a token. 32 bytes is 256 bits of entropy,
#: which is far more than enough for a credential with a one-hour lifetime.
TOKEN_BYTES = 32


def generate_token() -> str:
    """A fresh, random, URL-safe token."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    """The digest stored in the database.

    SHA-256 rather than bcrypt, and deliberately so: the token is 256 bits of
    random data, so there is no dictionary to attack and no need for a slow
    hash. A slow hash would only add latency to every verification attempt.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
