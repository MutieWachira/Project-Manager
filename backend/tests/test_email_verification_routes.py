import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import EmailVerificationToken, User
from app.services.email_verification import create_email_verification_token


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
def verification_account(api_database):
    with api_database() as db:
        user = User(
            full_name="Verification Test",
            email="verification@example.com",
            password_hash="test-password-hash",
            is_active=True,
        )

        db.add(user)
        db.flush()

        raw_token = create_email_verification_token(db, user)

        db.commit()

        return {
            "user_id": user.id,
            "token": raw_token,
        }


def test_valid_token_verifies_account(
    client,
    api_database,
    verification_account,
):
    response = client.post(
        "/api/v1/auth/verify-email",
        json={"token": verification_account["token"]},
    )

    assert response.status_code == 200

    with api_database() as db:
        user = db.get(User, verification_account["user_id"])

        assert user.email_verified_at is not None


def test_verification_token_can_only_be_used_once(
    client,
    verification_account,
):
    first_response = client.post(
        "/api/v1/auth/verify-email",
        json={"token": verification_account["token"]},
    )

    second_response = client.post(
        "/api/v1/auth/verify-email",
        json={"token": verification_account["token"]},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 400


def test_invalid_token_is_rejected(client):
    response = client.post(
        "/api/v1/auth/verify-email",
        json={"token": "invalid-verification-token-123456"},
    )

    assert response.status_code == 400


def test_expired_token_is_rejected(
    client,
    api_database,
    verification_account,
):
    with api_database() as db:
        token_record = db.scalar(
            select(EmailVerificationToken).where(
                EmailVerificationToken.user_id == verification_account["user_id"]
            )
        )

        from datetime import UTC, datetime, timedelta

        token_record.expires_at = datetime.now(UTC) - timedelta(minutes=5)
        db.commit()

    response = client.post(
        "/api/v1/auth/verify-email",
        json={"token": verification_account["token"]},
    )

    assert response.status_code == 400


def test_missing_token_is_rejected(client):
    response = client.post(
        "/api/v1/auth/verify-email",
        json={},
    )

    assert response.status_code == 422


def test_empty_token_is_rejected(client):
    response = client.post(
        "/api/v1/auth/verify-email",
        json={"token": ""},
    )

    assert response.status_code == 422
