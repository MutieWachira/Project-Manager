import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest


def test_valid_registration_data():
    registration = RegisterRequest(
        full_name="Christopher Wachira",
        email="developer@example.com",
        password="A-Strong-Test-Password-2026",
    )

    assert registration.full_name == "Christopher Wachira"
    assert registration.email == "developer@example.com"


def test_full_name_is_trimmed():
    registration = RegisterRequest(
        full_name="  Christopher Wachira  ",
        email="developer@example.com",
        password="A-Strong-Test-Password-2026",
    )

    assert registration.full_name == "Christopher Wachira"


def test_email_is_normalized():
    registration = RegisterRequest(
        full_name="Christopher Wachira",
        email="  DEVELOPER@EXAMPLE.COM  ",
        password="A-Strong-Test-Password-2026",
    )

    assert registration.email == "developer@example.com"


def test_invalid_email_is_rejected():
    with pytest.raises(ValidationError):
        RegisterRequest(
            full_name="Christopher Wachira",
            email="not-an-email",
            password="A-Strong-Test-Password-2026",
        )


def test_short_password_is_rejected():
    with pytest.raises(ValidationError):
        RegisterRequest(
            full_name="Christopher Wachira",
            email="developer@example.com",
            password="short",
        )


def test_short_name_is_rejected():
    with pytest.raises(ValidationError):
        RegisterRequest(
            full_name="C",
            email="developer@example.com",
            password="A-Strong-Test-Password-2026",
        )


def test_password_is_not_modified():
    password = "  A-Strong-Test-Password-2026  "

    registration = RegisterRequest(
        full_name="Christopher Wachira",
        email="developer@example.com",
        password=password,
    )

    assert registration.password == password


def test_login_defaults_to_web_client():
    from app.schemas.auth import LoginRequest

    request = LoginRequest(
        email="developer@example.com",
        password="A-Strong-Test-Password-2026",
    )

    assert request.client_type == "web"
    assert request.device_name is None


def test_login_accepts_mobile_client():
    from app.schemas.auth import LoginRequest

    request = LoginRequest(
        email="developer@example.com",
        password="A-Strong-Test-Password-2026",
        client_type="mobile",
        device_name="Android Phone",
    )

    assert request.client_type == "mobile"
    assert request.device_name == "Android Phone"


def test_login_rejects_unsupported_client_type():
    from app.schemas.auth import LoginRequest

    with pytest.raises(ValidationError):
        LoginRequest(
            email="developer@example.com",
            password="A-Strong-Test-Password-2026",
            client_type="desktop",
        )


def test_login_device_name_is_trimmed():
    from app.schemas.auth import LoginRequest

    request = LoginRequest(
        email="developer@example.com",
        password="A-Strong-Test-Password-2026",
        device_name="  Test Laptop  ",
    )

    assert request.device_name == "Test Laptop"


def test_mfa_challenge_request_accepts_code():
    from app.schemas.auth import MFAChallengeVerifyRequest

    request = MFAChallengeVerifyRequest(
        challenge_token="a" * 30,
        code="123456",
        device_name="Test Laptop",
    )

    assert request.code == "123456"
    assert request.device_name == "Test Laptop"


def test_mfa_challenge_request_does_not_reject_malformed_code():
    from app.schemas.auth import MFAChallengeVerifyRequest

    request = MFAChallengeVerifyRequest(
        challenge_token="a" * 30,
        code="abcdef",
    )

    assert request.code == "abcdef"


def test_mfa_challenge_request_rejects_missing_code():
    from app.schemas.auth import MFAChallengeVerifyRequest

    with pytest.raises(ValidationError):
        MFAChallengeVerifyRequest(
            challenge_token="a" * 30,
        )


def test_login_response_supports_mfa_challenge():
    from datetime import UTC, datetime

    from app.schemas.auth import LoginResponse

    response = LoginResponse(
        mfa_required=True,
        challenge_token="challenge-token",
        challenge_expires_at=datetime.now(UTC),
    )

    assert response.mfa_required is True
    assert response.challenge_token == "challenge-token"
    assert response.access_token is None
    assert response.refresh_token is None


def test_login_response_supports_completed_login():
    from app.schemas.auth import LoginResponse

    response = LoginResponse(
        access_token="access-token",
        refresh_token="mobile-refresh-token",
        expires_in=600,
        session_id="session-123",
    )

    assert response.mfa_required is False
    assert response.access_token == "access-token"
    assert response.refresh_token == "mobile-refresh-token"
