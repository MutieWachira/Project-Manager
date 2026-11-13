"""Secure refresh-token generation and hashing utilities."""

import hashlib
import secrets


def generate_refresh_token() -> str:
    """
    Generate a cryptographically secure refresh token.

    The returned token is intended to be delivered to the client.
    It must never be stored directly in the database or application logs.
    """

    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """
    Hash a refresh token using SHA-256.

    Only this hash should be stored in the database.

    Refresh tokens are high-entropy random credentials, so a fast
    cryptographic hash is appropriate here.
    """

    if not isinstance(token, str) or not token:
        raise ValueError("Refresh token cannot be empty.")

    return hashlib.sha256(token.encode("utf-8")).hexdigest()
