"""Encryption utilities for sensitive application secrets."""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class EncryptionError(ValueError):
    """Raised when sensitive data cannot be encrypted or decrypted."""


def _get_fernet() -> Fernet:
    """Build a Fernet cipher using the dedicated MFA encryption key."""

    key = settings.MFA_ENCRYPTION_KEY.get_secret_value()

    try:
        return Fernet(key.encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise EncryptionError("MFA encryption configuration is invalid.") from exc


def encrypt_secret(secret: str) -> str:
    """Encrypt a non-empty secret and return its encoded ciphertext."""

    if not isinstance(secret, str) or not secret:
        raise EncryptionError("Secret cannot be empty.")

    try:
        encrypted = _get_fernet().encrypt(secret.encode("utf-8"))

        return encrypted.decode("ascii")

    except EncryptionError:
        raise

    except Exception as exc:
        raise EncryptionError("Unable to encrypt the supplied secret.") from exc


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a previously encrypted secret."""

    if not isinstance(ciphertext, str) or not ciphertext:
        raise EncryptionError("Ciphertext cannot be empty.")

    try:
        decrypted = _get_fernet().decrypt(ciphertext.encode("ascii"))

        return decrypted.decode("utf-8")

    except (InvalidToken, UnicodeError, ValueError) as exc:
        raise EncryptionError("Unable to decrypt the supplied secret.") from exc
