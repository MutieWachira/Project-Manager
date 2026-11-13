import re

import pytest

from app.services.email_verification import (
    generate_verification_token,
    hash_verification_token,
)


def test_generated_token_is_not_empty():
    token = generate_verification_token()

    assert isinstance(token, str)
    assert token


def test_generated_tokens_are_different():
    first_token = generate_verification_token()
    second_token = generate_verification_token()

    assert first_token != second_token


def test_generated_token_has_sufficient_entropy():
    token = generate_verification_token()

    # token_urlsafe(32) produces a URL-safe token of sufficient length.
    assert len(token) >= 40


def test_token_hash_is_sha256_hex():
    token = generate_verification_token()

    hashed_token = hash_verification_token(token)

    assert len(hashed_token) == 64
    assert re.fullmatch(r"[0-9a-f]{64}", hashed_token)


def test_same_token_produces_same_hash():
    token = generate_verification_token()

    first_hash = hash_verification_token(token)
    second_hash = hash_verification_token(token)

    assert first_hash == second_hash


def test_different_tokens_produce_different_hashes():
    first_token = generate_verification_token()
    second_token = generate_verification_token()

    assert hash_verification_token(first_token) != hash_verification_token(second_token)


def test_hash_does_not_equal_raw_token():
    token = generate_verification_token()

    assert hash_verification_token(token) != token


def test_empty_token_hashing_is_deterministic():
    assert hash_verification_token("") == hash_verification_token("")


def test_invalid_expiry_is_rejected():
    from unittest.mock import MagicMock

    from app.services.email_verification import (
        create_email_verification_token,
    )

    db = MagicMock()
    user = MagicMock()

    with pytest.raises(ValueError):
        create_email_verification_token(
            db,
            user,
            expiry_minutes=0,
        )
