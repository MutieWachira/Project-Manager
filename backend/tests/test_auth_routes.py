import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import User
from app.services import authentication


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
def valid_registration():
    return {
        "full_name": "Test Developer",
        "email": "developer@example.com",
        "password": "A-Strong-Test-Password-2026",
    }


def test_registration_endpoint_returns_202(
    client,
    valid_registration,
    monkeypatch,
):
    sent_emails = []

    monkeypatch.setattr(
        authentication,
        "send_email_verification_email",
        lambda **kwargs: sent_emails.append(kwargs),
    )

    response = client.post(
        "/api/v1/auth/register",
        json=valid_registration,
    )

    assert response.status_code == 202
    assert "check your email" in response.json()["message"].lower()
    assert len(sent_emails) == 1


def test_registration_endpoint_creates_unverified_account(
    client,
    api_database,
    valid_registration,
    monkeypatch,
):
    monkeypatch.setattr(
        authentication,
        "send_email_verification_email",
        lambda **kwargs: None,
    )

    response = client.post(
        "/api/v1/auth/register",
        json=valid_registration,
    )

    assert response.status_code == 202

    with api_database() as db:
        user = db.scalar(select(User).where(User.email == valid_registration["email"]))

        assert user is not None
        assert user.email_verified_at is None


def test_duplicate_registration_returns_same_public_response(
    client,
    valid_registration,
    monkeypatch,
):
    sent_emails = []

    monkeypatch.setattr(
        authentication,
        "send_email_verification_email",
        lambda **kwargs: sent_emails.append(kwargs),
    )

    first_response = client.post(
        "/api/v1/auth/register",
        json=valid_registration,
    )

    second_response = client.post(
        "/api/v1/auth/register",
        json=valid_registration,
    )

    assert first_response.status_code == 202
    assert second_response.status_code == 202
    assert first_response.json() == second_response.json()
    assert len(sent_emails) == 1


def test_registration_rejects_invalid_email(
    client,
    valid_registration,
):
    valid_registration["email"] = "not-an-email"

    response = client.post(
        "/api/v1/auth/register",
        json=valid_registration,
    )

    assert response.status_code == 422


def test_registration_rejects_short_password(
    client,
    valid_registration,
):
    valid_registration["password"] = "short"

    response = client.post(
        "/api/v1/auth/register",
        json=valid_registration,
    )

    assert response.status_code == 422


def test_registration_rejects_missing_fields(client):
    response = client.post(
        "/api/v1/auth/register",
        json={},
    )

    assert response.status_code == 422
