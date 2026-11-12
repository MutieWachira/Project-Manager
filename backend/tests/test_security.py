import pytest

from app.core.security import hash_password, verify_password


def test_password_is_hashed():
    password = "A-Strong-Test-Password-2026"

    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2id$")


def test_correct_password_is_verified():
    password = "A-Strong-Test-Password-2026"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_incorrect_password_is_rejected():
    hashed = hash_password("A-Strong-Test-Password-2026")

    assert verify_password("Incorrect-Password-2026", hashed) is False


def test_empty_password_cannot_be_hashed():
    with pytest.raises(ValueError):
        hash_password("")


def test_empty_password_cannot_be_verified():
    hashed = hash_password("A-Strong-Test-Password-2026")

    assert verify_password("", hashed) is False


def test_empty_hash_cannot_be_verified():
    assert verify_password("A-Strong-Test-Password-2026", "") is False
