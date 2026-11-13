"""Tests for sensitive-data encryption utilities."""

import pytest

from cryptography.fernet import Fernet
from pydantic import SecretStr

from app.core import encryption
from app.core.config import settings
from app.core.encryption import (
    EncryptionError,
    decrypt_secret,
    encrypt_secret,
)


@pytest.fixture
def test_encryption_key(monkeypatch):
    """Provide an isolated encryption key for each test."""

    key = Fernet.generate_key().decode("ascii")

    monkeypatch.setattr(
        settings,
        "MFA_ENCRYPTION_KEY",
        SecretStr(key),
    )

    return key


def test_encrypt_and_decrypt_secret(test_encryption_key):
    secret = "test-authenticator-secret"

    encrypted = encrypt_secret(secret)

    assert encrypted != secret
    assert decrypt_secret(encrypted) == secret


def test_encryption_produces_different_ciphertexts(
    test_encryption_key,
):
    secret = "test-authenticator-secret"

    first = encrypt_secret(secret)
    second = encrypt_secret(secret)

    assert first != second

    assert decrypt_secret(first) == secret
    assert decrypt_secret(second) == secret


def test_encrypted_value_does_not_contain_plaintext(
    test_encryption_key,
):
    secret = "private-authenticator-secret"

    encrypted = encrypt_secret(secret)

    assert secret not in encrypted


def test_empty_secret_is_rejected(test_encryption_key):
    with pytest.raises(EncryptionError):
        encrypt_secret("")


def test_empty_ciphertext_is_rejected(test_encryption_key):
    with pytest.raises(EncryptionError):
        decrypt_secret("")


def test_tampered_ciphertext_is_rejected(test_encryption_key):
    encrypted = encrypt_secret("test-secret")

    tampered = encrypted[:-4] + "AAAA"

    with pytest.raises(EncryptionError):
        decrypt_secret(tampered)


def test_wrong_encryption_key_is_rejected(
    test_encryption_key,
    monkeypatch,
):
    encrypted = encrypt_secret("test-secret")

    different_key = Fernet.generate_key().decode("ascii")

    monkeypatch.setattr(
        settings,
        "MFA_ENCRYPTION_KEY",
        SecretStr(different_key),
    )

    with pytest.raises(EncryptionError):
        decrypt_secret(encrypted)


def test_invalid_ciphertext_is_rejected(test_encryption_key):
    with pytest.raises(EncryptionError):
        decrypt_secret("this-is-not-valid-fernet-ciphertext")
