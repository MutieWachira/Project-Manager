"""Tests for JWT access-token creation and validation."""

from datetime import timedelta

import pytest
from jose import jwt

from app.core.config import settings
from app.core.tokens import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
)


def test_create_and_decode_access_token():
    token = create_access_token("user-123")

    payload = decode_access_token(token)

    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert payload["iss"] == settings.JWT_ISSUER
    assert payload["aud"] == settings.JWT_AUDIENCE
    assert "jti" in payload
    assert "exp" in payload
    assert "iat" in payload


def test_token_contains_unique_identifier():
    first_token = create_access_token("user-123")
    second_token = create_access_token("user-123")

    first_payload = decode_access_token(first_token)
    second_payload = decode_access_token(second_token)

    assert first_payload["jti"] != second_payload["jti"]


def test_empty_subject_is_rejected():
    with pytest.raises(ValueError):
        create_access_token("")


def test_whitespace_subject_is_rejected():
    with pytest.raises(ValueError):
        create_access_token("   ")


def test_expired_token_is_rejected():
    token = create_access_token(
        "user-123",
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_malformed_token_is_rejected():
    with pytest.raises(InvalidTokenError):
        decode_access_token("this-is-not-a-valid-jwt")


def test_empty_token_is_rejected():
    with pytest.raises(InvalidTokenError):
        decode_access_token("")


def test_token_signed_with_wrong_secret_is_rejected():
    token = jwt.encode(
        {
            "sub": "user-123",
            "type": "access",
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
        },
        "incorrect-signing-secret-that-is-not-used",
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_non_access_token_type_is_rejected():
    token = jwt.encode(
        {
            "sub": "user-123",
            "type": "refresh",
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
        },
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)
