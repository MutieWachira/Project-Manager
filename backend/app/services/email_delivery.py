
from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from urllib.parse import urlencode

from app.core.config import settings


class EmailDeliveryError(Exception):
    """Raised when an email cannot be delivered."""


def build_verification_url(token: str) -> str:
    """Build the frontend URL used to verify an email address."""
    if not token:
        raise ValueError("Verification token cannot be empty.")

    query = urlencode({"token": token})

    return f"{settings.FRONTEND_URL.rstrip('/')}/verify-email?{query}"


def build_verification_email(
    recipient_email: str,
    recipient_name: str,
    verification_url: str,
) -> EmailMessage:
    """Build a multipart plain-text and HTML verification email."""
    message = EmailMessage()

    message["Subject"] = f"Verify your {settings.APP_NAME} email address"
    message["From"] = formataddr(
        (settings.MAIL_FROM_NAME, settings.MAIL_FROM)
    )
    message["To"] = recipient_email

    plain_text = f"""
Hello {recipient_name},

Welcome to {settings.APP_NAME}.

Please open the following link to verify your email address:

{verification_url}

This verification link expires in 30 minutes.

If you did not create this account, you can ignore this email.

Regards,
{settings.MAIL_FROM_NAME}
""".strip()

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify your email</title>
</head>
<body style="font-family: Arial, sans-serif; color: #1f2937;">
    <main style="max-width: 600px; margin: 30px auto; padding: 24px;">
        <h1>Welcome to {settings.APP_NAME}</h1>

        <p>Hello {recipient_name},</p>

        <p>
            Thank you for creating your account.
            Please verify your email address to continue.
        </p>

        <p style="margin: 30px 0;">
            <a href="{verification_url}"
               style="background: #2563eb; color: white;
                      padding: 14px 24px; text-decoration: none;
                      border-radius: 6px;">
                Verify email address
            </a>
        </p>

        <p>This link expires in 30 minutes.</p>

        <p>If you did not create this account, ignore this email.</p>

        <p>Regards,<br>{settings.MAIL_FROM_NAME}</p>
    </main>
</body>
</html>
""".strip()

    message.set_content(plain_text)
    message.add_alternative(html_content, subtype="html")

    return message


def send_email_verification_email(
    recipient_email: str,
    recipient_name: str,
    token: str,
) -> None:
    """
    Send an email verification message through SMTP.

    Supports optional SMTP authentication and STARTTLS.
    The verification token is included in the email but is never logged.
    """
    if not recipient_email or not recipient_name:
        raise ValueError("Recipient email and name are required.")

    if not token:
        raise ValueError("Verification token is required.")

    username = settings.MAIL_USERNAME
    password = settings.MAIL_PASSWORD

    if bool(username) != bool(password):
        raise ValueError(
            "Both SMTP username and password must be configured together."
        )

    verification_url = build_verification_url(token)

    message = build_verification_email(
        recipient_email=recipient_email,
        recipient_name=recipient_name,
        verification_url=verification_url,
    )

    try:
        with smtplib.SMTP(
            settings.MAIL_HOST,
            settings.MAIL_PORT,
            timeout=settings.MAIL_TIMEOUT,
        ) as smtp:
            if settings.MAIL_STARTTLS:
                smtp.starttls(context=ssl.create_default_context())

            if username and password:
                smtp.login(username, password)

            refused_recipients = smtp.send_message(message)

            if refused_recipients:
                raise EmailDeliveryError(
                    "The SMTP server refused the recipient address."
                )

    except EmailDeliveryError:
        raise

    except (smtplib.SMTPException, OSError) as exc:
        raise EmailDeliveryError(
            "Unable to deliver the verification email."
        ) from exc
