
from email.message import EmailMessage
from unittest.mock import MagicMock, patch

import pytest

from app.services.email_delivery import (
    EmailDeliveryError,
    build_verification_email,
    build_verification_url,
    send_email_verification_email,
)


def test_build_verification_url():
    url = build_verification_url("test-token")

    assert url.startswith("http://localhost:3000/verify-email?")
    assert "token=test-token" in url


def test_build_verification_url_rejects_empty_token():
    with pytest.raises(ValueError):
        build_verification_url("")


def test_build_verification_email_contains_plain_text_and_html():
    message = build_verification_email(
        recipient_email="user@example.com",
        recipient_name="Test User",
        verification_url="http://localhost:3000/verify-email?token=test",
    )

    assert isinstance(message, EmailMessage)
    assert message["To"] == "user@example.com"
    assert message.is_multipart()
    assert message.get_body(preferencelist=("plain",)) is not None
    assert message.get_body(preferencelist=("html",)) is not None


def test_send_verification_email_success():
    smtp_instance = MagicMock()
    smtp_instance.send_message.return_value = {}

    with patch(
        "app.services.email_delivery.smtplib.SMTP"
    ) as smtp_factory:
        smtp_factory.return_value.__enter__.return_value = smtp_instance

        send_email_verification_email(
            "user@example.com",
            "Test User",
            "test-token",
        )

    smtp_factory.assert_called_once()
    smtp_instance.send_message.assert_called_once()

    sent_message = smtp_instance.send_message.call_args.args[0]

    assert sent_message["To"] == "user@example.com"
    assert "test-token" in sent_message.get_body(
        preferencelist=("plain",)
    ).get_content()


def test_send_verification_email_rejects_missing_recipient():
    with pytest.raises(ValueError):
        send_email_verification_email(
            "",
            "Test User",
            "test-token",
        )


def test_send_verification_email_rejects_empty_token():
    with pytest.raises(ValueError):
        send_email_verification_email(
            "user@example.com",
            "Test User",
            "",
        )


def test_smtp_failure_raises_delivery_error():
    with patch(
        "app.services.email_delivery.smtplib.SMTP"
    ) as smtp_factory:
        smtp_factory.side_effect = OSError("SMTP unavailable")

        with pytest.raises(EmailDeliveryError):
            send_email_verification_email(
                "user@example.com",
                "Test User",
                "test-token",
            )


def test_refused_recipient_raises_delivery_error():
    smtp_instance = MagicMock()
    smtp_instance.send_message.return_value = {
        "user@example.com": (550, b"Recipient rejected")
    }

    with patch(
        "app.services.email_delivery.smtplib.SMTP"
    ) as smtp_factory:
        smtp_factory.return_value.__enter__.return_value = smtp_instance

        with pytest.raises(EmailDeliveryError):
            send_email_verification_email(
                "user@example.com",
                "Test User",
                "test-token",
            )
