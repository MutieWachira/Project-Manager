"""Tests for JWT access-token creation and validation."""

from datetime import timedelta
from uuid import uuid4

import pytest
from jose import jwt

from app.core.config import settings
from app.core.tokens import (
    InvalidTokenError,
    create_access_token,
    create_mfa_challenge_token,
    decode_access_token,
    decode_mfa_challenge_token,
    decode_session_access_token,
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


def test_create_and_decode_mfa_challenge_token():
    challenge_id = uuid4()

    token = create_mfa_challenge_token(
        "user-123",
        challenge_id=challenge_id,
    )

    payload = decode_mfa_challenge_token(token)

    assert payload["sub"] == "user-123"
    assert payload["type"] == "mfa_challenge"
    assert payload["jti"] == str(challenge_id)
    assert payload["iss"] == settings.JWT_ISSUER
    assert payload["aud"] == settings.JWT_AUDIENCE


def test_mfa_challenge_token_cannot_be_used_as_access_token():
    token = create_mfa_challenge_token(
        "user-123",
        challenge_id=uuid4(),
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_mfa_challenge_token_cannot_be_used_as_session_token():
    token = create_mfa_challenge_token(
        "user-123",
        challenge_id=uuid4(),
    )

    with pytest.raises(InvalidTokenError):
        decode_session_access_token(token)


def test_mfa_challenge_token_rejects_invalid_challenge_id():
    with pytest.raises(ValueError):
        create_mfa_challenge_token(
            "user-123",
            challenge_id="not-a-uuid",
        )


def test_mfa_challenge_token_rejects_empty_subject():
    with pytest.raises(ValueError):
        create_mfa_challenge_token(
            "",
            challenge_id=uuid4(),
        )


def test_mfa_challenge_token_rejects_non_positive_expiry():
    from datetime import timedelta

    with pytest.raises(ValueError):
        create_mfa_challenge_token(
            "user-123",
            challenge_id=uuid4(),
            expires_delta=timedelta(seconds=0),
        )


def test_mfa_challenge_decoder_rejects_access_token():
    access_token = create_access_token("user-123")

    with pytest.raises(InvalidTokenError):
        decode_mfa_challenge_token(access_token)


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


def test_session_access_token_contains_session_id():
    from uuid import uuid4

    from app.core.tokens import create_session_access_token

    session_id = uuid4()

    token = create_session_access_token(
        "user-123",
        session_id=session_id,
    )

    payload = decode_access_token(token)

    assert payload["sub"] == "user-123"
    assert payload["sid"] == str(session_id)
    assert payload["type"] == "access"


def test_session_access_token_accepts_string_session_id():
    from uuid import uuid4

    from app.core.tokens import create_session_access_token

    session_id = str(uuid4())

    token = create_session_access_token(
        "user-123",
        session_id=session_id,
    )

    payload = decode_access_token(token)

    assert payload["sid"] == session_id


def test_session_access_token_rejects_invalid_session_id():
    from app.core.tokens import create_session_access_token

    with pytest.raises(ValueError):
        create_session_access_token(
            "user-123",
            session_id="not-a-uuid",
        )


def test_session_access_token_rejects_empty_subject():
    from uuid import uuid4

    from app.core.tokens import create_session_access_token

    with pytest.raises(ValueError):
        create_session_access_token(
            "",
            session_id=uuid4(),
        )


def test_session_decoder_accepts_valid_session_token():
    from uuid import uuid4

    from app.core.tokens import (
        create_session_access_token,
        decode_session_access_token,
    )

    session_id = uuid4()

    token = create_session_access_token(
        "user-123",
        session_id=session_id,
    )

    payload = decode_session_access_token(token)

    assert payload["sub"] == "user-123"
    assert payload["sid"] == str(session_id)


def test_session_decoder_rejects_legacy_token():
    from app.core.tokens import decode_session_access_token

    legacy_token = create_access_token("user-123")

    with pytest.raises(InvalidTokenError):
        decode_session_access_token(legacy_token)


def test_session_decoder_rejects_invalid_session_claim():
    from jose import jwt

    from app.core.tokens import decode_session_access_token

    token = jwt.encode(
        {
            "sub": "user-123",
            "sid": "invalid-session-id",
            "type": "access",
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
        },
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(InvalidTokenError):
        decode_session_access_token(token)
