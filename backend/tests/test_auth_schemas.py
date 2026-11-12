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
