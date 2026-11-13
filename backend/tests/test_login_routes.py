from datetime import UTC, datetime
from uuid import UUID

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.encryption import encrypt_secret
from app.core.security import hash_password
from app.core.tokens import decode_session_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import (
    MFALoginChallenge,
    RefreshToken,
    User,
    UserMFA,
    UserSession,
)


@pytest.fixture
def api_database():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    test_session = sessionmaker(
        bind=engine,
        class_=Session,
        expire_on_commit=False,
    )

    def override_get_db():
        db = test_session()

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield test_session
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(api_database):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def verified_user(api_database):
    with api_database() as db:
        user = User(
            full_name="Test Developer",
            email="developer@example.com",
            password_hash=hash_password("A-Strong-Test-Password-2026"),
            is_active=True,
            email_verified_at=datetime.now(UTC),
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user.id


@pytest.fixture
def mfa_enabled_user(api_database):
    """Create a verified account with an enabled TOTP authenticator."""

    now = datetime.now(UTC)
    secret = pyotp.random_base32()

    with api_database() as db:
        user = User(
            full_name="MFA Test Developer",
            email="mfa-developer@example.com",
            password_hash=hash_password("A-Strong-Test-Password-2026"),
            is_active=True,
            email_verified_at=now,
        )

        mfa = UserMFA(
            user=user,
            encrypted_secret=encrypt_secret(secret),
            is_enabled=True,
            confirmed_at=now,
        )

        db.add_all([user, mfa])
        db.commit()
        db.refresh(user)

        user_id = user.id

    return user_id, secret


def test_web_login_creates_session_and_refresh_cookie(
    client,
    verified_user,
):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "developer@example.com",
            "password": "A-Strong-Test-Password-2026",
            "client_type": "web",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["mfa_required"] is False
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 600
    assert isinstance(data["access_token"], str)
    assert data["refresh_token"] is None
    assert data["session_id"] is not None

    payload = decode_session_access_token(data["access_token"])

    assert payload["sub"] == str(verified_user)
    assert payload["sid"] == data["session_id"]

    cookie = response.cookies.get("sherlskyycommand_refresh")
    assert cookie is not None


def test_mobile_login_returns_refresh_token_in_response(
    client,
    verified_user,
):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "developer@example.com",
            "password": "A-Strong-Test-Password-2026",
            "client_type": "mobile",
            "device_name": "Test Android",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["mfa_required"] is False
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["session_id"]

    assert "sherlskyycommand_refresh" not in response.cookies


@pytest.mark.parametrize(
    "email,password",
    [
        ("unknown@example.com", "A-Strong-Test-Password-2026"),
        ("developer@example.com", "Wrong-Password-2026"),
    ],
)
def test_login_returns_generic_error_for_invalid_credentials(
    client,
    verified_user,
    email,
    password,
):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_login_rejects_unverified_account(client, api_database):
    with api_database() as db:
        db.add(
            User(
                full_name="Unverified Developer",
                email="unverified@example.com",
                password_hash=hash_password("A-Strong-Test-Password-2026"),
                is_active=True,
            )
        )
        db.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "unverified@example.com",
            "password": "A-Strong-Test-Password-2026",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_login_rejects_inactive_account(client, api_database):
    with api_database() as db:
        db.add(
            User(
                full_name="Inactive Developer",
                email="inactive@example.com",
                password_hash=hash_password("A-Strong-Test-Password-2026"),
                is_active=False,
                email_verified_at=datetime.now(UTC),
            )
        )
        db.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "inactive@example.com",
            "password": "A-Strong-Test-Password-2026",
        },
    )

    assert response.status_code == 401


def test_login_rejects_invalid_request(client):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "not-an-email",
            "password": "password",
        },
    )

    assert response.status_code == 422


def test_web_mfa_login_completes_with_refresh_cookie(
    client,
    mfa_enabled_user,
):
    _, secret = mfa_enabled_user

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "mfa-developer@example.com",
            "password": "A-Strong-Test-Password-2026",
            "client_type": "web",
        },
    )

    assert login_response.status_code == 200

    challenge_data = login_response.json()

    assert challenge_data["mfa_required"] is True
    assert challenge_data["challenge_token"]
    assert challenge_data["challenge_expires_at"] is not None
    assert challenge_data["access_token"] is None
    assert challenge_data["refresh_token"] is None
    assert challenge_data["session_id"] is None
    assert "sherlskyycommand_refresh" not in login_response.cookies

    verification_response = client.post(
        "/api/v1/auth/mfa/verify",
        json={
            "challenge_token": challenge_data["challenge_token"],
            "code": pyotp.TOTP(secret).now(),
            "device_name": "Test Laptop",
        },
        headers={"user-agent": "SherlskyyCommand Test Browser"},
    )

    assert verification_response.status_code == 200

    data = verification_response.json()

    assert data["mfa_required"] is False
    assert data["access_token"]
    assert data["refresh_token"] is None
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 600
    assert data["session_id"]

    payload = decode_session_access_token(data["access_token"])

    assert payload["sub"] == str(mfa_enabled_user[0])
    assert payload["sid"] == data["session_id"]

    cookie = verification_response.cookies.get("sherlskyycommand_refresh")

    assert cookie is not None


def test_mobile_mfa_login_returns_refresh_token(
    client,
    mfa_enabled_user,
):
    _, secret = mfa_enabled_user

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "mfa-developer@example.com",
            "password": "A-Strong-Test-Password-2026",
            "client_type": "mobile",
        },
    )

    assert login_response.status_code == 200

    challenge_data = login_response.json()

    assert challenge_data["mfa_required"] is True
    assert challenge_data["challenge_token"]
    assert "sherlskyycommand_refresh" not in login_response.cookies

    verification_response = client.post(
        "/api/v1/auth/mfa/verify",
        json={
            "challenge_token": challenge_data["challenge_token"],
            "code": pyotp.TOTP(secret).now(),
            "device_name": "Test Android",
        },
        headers={"user-agent": "SherlskyyCommand Android"},
    )

    assert verification_response.status_code == 200

    data = verification_response.json()

    assert data["mfa_required"] is False
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["session_id"]

    payload = decode_session_access_token(data["access_token"])

    assert payload["sub"] == str(mfa_enabled_user[0])
    assert payload["sid"] == data["session_id"]

    assert "sherlskyycommand_refresh" not in verification_response.cookies


def test_successful_mfa_challenge_cannot_be_reused(
    client,
    api_database,
    mfa_enabled_user,
):
    user_id, secret = mfa_enabled_user

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "mfa-developer@example.com",
            "password": "A-Strong-Test-Password-2026",
            "client_type": "web",
        },
    )

    assert login_response.status_code == 200

    challenge_token = login_response.json()["challenge_token"]
    code = pyotp.TOTP(secret).now()

    first_verification = client.post(
        "/api/v1/auth/mfa/verify",
        json={
            "challenge_token": challenge_token,
            "code": code,
        },
    )

    assert first_verification.status_code == 200

    second_verification = client.post(
        "/api/v1/auth/mfa/verify",
        json={
            "challenge_token": challenge_token,
            "code": code,
        },
    )

    assert second_verification.status_code == 401

    with api_database() as db:
        sessions = db.scalars(
            select(UserSession).where(UserSession.user_id == user_id)
        ).all()

        challenge = db.scalar(
            select(MFALoginChallenge).where(MFALoginChallenge.user_id == user_id)
        )

        assert len(sessions) == 1
        assert challenge is not None
        assert challenge.consumed_at is not None


def test_invalid_mfa_code_does_not_create_session(
    client,
    api_database,
    mfa_enabled_user,
):
    user_id, _ = mfa_enabled_user

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "mfa-developer@example.com",
            "password": "A-Strong-Test-Password-2026",
            "client_type": "web",
        },
    )

    assert login_response.status_code == 200

    challenge_token = login_response.json()["challenge_token"]

    verification_response = client.post(
        "/api/v1/auth/mfa/verify",
        json={
            "challenge_token": challenge_token,
            "code": "abcdef",
        },
    )

    assert verification_response.status_code == 401
    assert verification_response.json()["detail"] == (
        "MFA verification failed or the challenge has expired."
    )

    with api_database() as db:
        challenge = db.scalar(
            select(MFALoginChallenge).where(MFALoginChallenge.user_id == user_id)
        )

        sessions = db.scalars(
            select(UserSession).where(UserSession.user_id == user_id)
        ).all()

        assert challenge is not None
        assert challenge.failed_attempts == 1
        assert challenge.consumed_at is None
        assert challenge.revoked_at is None

        assert sessions == []


def test_web_refresh_rotates_cookie_and_returns_new_access_token(
    client,
    verified_user,
):
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "developer@example.com",
            "password": "A-Strong-Test-Password-2026",
            "client_type": "web",
        },
    )

    assert login_response.status_code == 200

    original_refresh_token = login_response.cookies.get("sherlskyycommand_refresh")
    assert original_refresh_token

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        headers={"Origin": "http://localhost:3000"},
    )

    assert refresh_response.status_code == 200

    data = refresh_response.json()

    assert data["access_token"]
    assert data["refresh_token"] is None
    assert data["session_id"]
    assert data["session_expires_at"]

    payload = decode_session_access_token(data["access_token"])

    assert payload["sub"] == str(verified_user)
    assert payload["sid"] == data["session_id"]

    replacement_refresh_token = refresh_response.cookies.get("sherlskyycommand_refresh")

    assert replacement_refresh_token
    assert replacement_refresh_token != original_refresh_token


def test_mobile_refresh_rotates_token_in_response(
    client,
    verified_user,
):
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "developer@example.com",
            "password": "A-Strong-Test-Password-2026",
            "client_type": "mobile",
            "device_name": "Test Android",
        },
    )

    assert login_response.status_code == 200

    original_refresh_token = login_response.json()["refresh_token"]

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original_refresh_token},
    )

    assert refresh_response.status_code == 200

    data = refresh_response.json()

    assert data["access_token"]
    assert data["refresh_token"]
    assert data["refresh_token"] != original_refresh_token
    assert data["session_id"]
    assert data["session_expires_at"]

    payload = decode_session_access_token(data["access_token"])

    assert payload["sub"] == str(verified_user)
    assert payload["sid"] == data["session_id"]

    assert "sherlskyycommand_refresh" not in refresh_response.cookies


def test_web_refresh_rejects_wrong_origin_without_consuming_token(
    client,
    verified_user,
):
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "developer@example.com",
            "password": "A-Strong-Test-Password-2026",
            "client_type": "web",
        },
    )

    assert login_response.status_code == 200

    original_refresh_token = login_response.cookies.get("sherlskyycommand_refresh")
    assert original_refresh_token

    rejected_response = client.post(
        "/api/v1/auth/refresh",
        headers={"Origin": "https://attacker.example"},
    )

    assert rejected_response.status_code == 403

    # The original token must remain usable after an origin rejection.
    assert client.cookies.get("sherlskyycommand_refresh") == original_refresh_token

    accepted_response = client.post(
        "/api/v1/auth/refresh",
        headers={"Origin": "http://localhost:3000"},
    )

    assert accepted_response.status_code == 200


def test_mobile_refresh_rejects_invalid_token(client):
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid-refresh-token-" * 3},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == ("Invalid or expired refresh token.")


def test_refresh_rejects_cookie_and_body_credentials_together(
    client,
    verified_user,
):
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "developer@example.com",
            "password": "A-Strong-Test-Password-2026",
            "client_type": "web",
        },
    )

    assert login_response.status_code == 200

    cookie_token = login_response.cookies.get("sherlskyycommand_refresh")
    assert cookie_token

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": cookie_token},
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid refresh request."


def test_web_logout_revokes_session_and_clears_cookie(
    client,
    verified_user,
    api_database,
):
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "developer@example.com",
            "password": "A-Strong-Test-Password-2026",
            "client_type": "web",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]
    refresh_token = login_response.cookies.get("sherlskyycommand_refresh")
    session_id = login_response.json()["session_id"]

    assert refresh_token

    logout_response = client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "http://localhost:3000"},
        cookies={"sherlskyycommand_refresh": refresh_token},
    )

    assert logout_response.status_code == 200
    assert logout_response.json()["message"] == ("You have been logged out.")
    assert "Max-Age=0" in logout_response.headers["set-cookie"]

    with api_database() as db:
        session = db.get(UserSession, UUID(session_id))

        assert session is not None
        assert session.revoked_at is not None
        assert session.revoke_reason == "user_logout"

        tokens = db.scalars(
            select(RefreshToken).where(RefreshToken.session_id == session.id)
        ).all()

        assert tokens
        assert all(token.revoked_at is not None for token in tokens)

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert me_response.status_code == 401

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        headers={"Origin": "http://localhost:3000"},
        cookies={"sherlskyycommand_refresh": refresh_token},
    )

    assert refresh_response.status_code == 401


def test_mobile_logout_revokes_session_and_refresh_token(
    client,
    verified_user,
    api_database,
):
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "developer@example.com",
            "password": "A-Strong-Test-Password-2026",
            "client_type": "mobile",
            "device_name": "Test Android",
        },
    )

    assert login_response.status_code == 200

    data = login_response.json()
    access_token = data["access_token"]
    refresh_token = data["refresh_token"]
    session_id = data["session_id"]

    logout_response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )

    assert logout_response.status_code == 200
    assert logout_response.json()["message"] == ("You have been logged out.")

    with api_database() as db:
        session = db.get(UserSession, UUID(session_id))

        assert session is not None
        assert session.revoked_at is not None

        tokens = db.scalars(
            select(RefreshToken).where(RefreshToken.session_id == session.id)
        ).all()

        assert tokens
        assert all(token.revoked_at is not None for token in tokens)

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert me_response.status_code == 401

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert refresh_response.status_code == 401


def test_web_logout_rejects_wrong_origin_without_revoking_session(
    client,
    verified_user,
    api_database,
):
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "developer@example.com",
            "password": "A-Strong-Test-Password-2026",
            "client_type": "web",
        },
    )

    assert login_response.status_code == 200

    refresh_token = login_response.cookies.get("sherlskyycommand_refresh")
    session_id = login_response.json()["session_id"]

    response = client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "https://attacker.example"},
        cookies={"sherlskyycommand_refresh": refresh_token},
    )

    assert response.status_code == 403

    with api_database() as db:
        session = db.get(UserSession, UUID(session_id))

        assert session is not None
        assert session.revoked_at is None


def test_logout_rejects_cookie_and_body_credentials_together(
    client,
    verified_user,
    api_database,
):
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "developer@example.com",
            "password": "A-Strong-Test-Password-2026",
            "client_type": "web",
        },
    )

    assert login_response.status_code == 200

    refresh_token = login_response.cookies.get("sherlskyycommand_refresh")
    session_id = login_response.json()["session_id"]

    response = client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "http://localhost:3000"},
        cookies={"sherlskyycommand_refresh": refresh_token},
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 400

    with api_database() as db:
        session = db.get(UserSession, UUID(session_id))

        assert session is not None
        assert session.revoked_at is None


def test_mobile_logout_with_invalid_token_is_idempotent(client):
    response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "invalid-refresh-token-" * 3},
    )

    assert response.status_code == 200
    assert response.json()["message"] == ("You have been logged out.")


def test_mobile_refresh_token_cannot_revoke_web_session(
    client,
    verified_user,
    api_database,
):
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "developer@example.com",
            "password": "A-Strong-Test-Password-2026",
            "client_type": "mobile",
        },
    )

    assert login_response.status_code == 200

    refresh_token = login_response.json()["refresh_token"]
    session_id = login_response.json()["session_id"]

    # Present a mobile token through the browser-cookie channel.
    response = client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "http://localhost:3000"},
        cookies={"sherlskyycommand_refresh": refresh_token},
    )

    assert response.status_code == 200

    with api_database() as db:
        session = db.get(UserSession, UUID(session_id))

        assert session is not None
        assert session.revoked_at is None
