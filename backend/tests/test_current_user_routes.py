"""Integration tests for the current-user authentication route."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.core.tokens import create_session_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import User, UserSession


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
def authenticated_user(api_database):
    with api_database() as db:
        user = User(
            full_name="Test Developer",
            email="developer@example.com",
            password_hash=hash_password("A-Strong-Test-Password-2026"),
            is_active=True,
            email_verified_at=datetime.now(UTC),
        )

        db.add(user)
        db.flush()

        authenticated_session = UserSession(
            user_id=user.id,
            client_type="web",
            device_name="Test Browser",
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )

        db.add(authenticated_session)
        db.commit()
        db.refresh(user)
        db.refresh(authenticated_session)

        token = create_session_access_token(
            str(user.id),
            session_id=authenticated_session.id,
        )

        return {
            "id": str(user.id),
            "session_id": str(authenticated_session.id),
            "token": token,
        }


def test_me_returns_authenticated_user(
    client,
    authenticated_user,
):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": (f"Bearer {authenticated_user['token']}")},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == authenticated_user["id"]
    assert data["full_name"] == "Test Developer"
    assert data["email"] == "developer@example.com"
    assert data["is_active"] is True
    assert data["email_verified"] is True

    assert "password_hash" not in data


def test_me_rejects_missing_token(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_me_rejects_invalid_token(client):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_me_rejects_deleted_user(
    client,
    authenticated_user,
    api_database,
):
    with api_database() as db:
        user = db.get(User, UUID(authenticated_user["id"]))
        db.delete(user)
        db.commit()

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": (f"Bearer {authenticated_user['token']}")},
    )

    assert response.status_code == 401


def test_me_rejects_revoked_session(
    client,
    authenticated_user,
    api_database,
):
    with api_database() as db:
        authenticated_session = db.get(
            UserSession,
            UUID(authenticated_user["session_id"]),
        )
        authenticated_session.revoked_at = datetime.now(UTC)
        db.commit()

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": (f"Bearer {authenticated_user['token']}")},
    )

    assert response.status_code == 401
