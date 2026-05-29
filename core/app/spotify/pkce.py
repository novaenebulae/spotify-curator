from __future__ import annotations

import base64
import hashlib
import os
import secrets


def generate_code_verifier(length: int = 64) -> str:
    # RFC 7636 allows 43-128 chars. We generate URL-safe and trim.
    raw = base64.urlsafe_b64encode(os.urandom(96)).decode("ascii").rstrip("=")
    if len(raw) < 43:
        raw = raw + secrets.token_urlsafe(64)
    return raw[: max(43, min(length, 128))]


def code_challenge_s256(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

