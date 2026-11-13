"""Tests for secure refresh-token generation and hashing."""

import re

import pytest

from app.core.refresh_tokens import (
    generate_refresh_token,
    hash_refresh_token,
)


def test_generate_refresh_token_returns_secure_random_value():
    token = generate_refresh_token()

    assert isinstance(token, str)
    assert len(token) >= 64
    assert re.fullmatch(r"[A-Za-z0-9_-]+", token)


def test_generate_refresh_token_generates_unique_values():
    tokens = {generate_refresh_token() for _ in range(100)}

    assert len(tokens) == 100


def test_hash_refresh_token_returns_sha256_hash():
    token = "example-refresh-token"

    token_hash = hash_refresh_token(token)

    assert len(token_hash) == 64
    assert re.fullmatch(r"[0-9a-f]{64}", token_hash)


def test_hash_refresh_token_is_deterministic():
    token = generate_refresh_token()

    first_hash = hash_refresh_token(token)
    second_hash = hash_refresh_token(token)

    assert first_hash == second_hash


def test_different_tokens_produce_different_hashes():
    first_hash = hash_refresh_token("first-refresh-token")
    second_hash = hash_refresh_token("second-refresh-token")

    assert first_hash != second_hash


@pytest.mark.parametrize(
    "token",
    [
        "",
        None,
    ],
)
def test_hash_refresh_token_rejects_empty_or_missing_values(token):
    with pytest.raises(ValueError):
        hash_refresh_token(token)
