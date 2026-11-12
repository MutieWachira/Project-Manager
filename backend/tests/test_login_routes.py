
from datetime import UTC, datetime

import pytest

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from app.core.security import hash_password
from app.core.tokens import decode_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import User


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
            password_hash=hash_password(
                "A-Strong-Test-Password-2026"
            ),
            is_active=True,
            email_verified_at=datetime.now(UTC),
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user.id


def test_login_returns_access_token(client, verified_user):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "developer@example.com",
            "password": "A-Strong-Test-Password-2026",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 600
    assert isinstance(data["access_token"], str)

    payload = decode_access_token(data["access_token"])

    assert payload["sub"] == str(verified_user)


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
                password_hash=hash_password(
                    "A-Strong-Test-Password-2026"
                ),
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
                password_hash=hash_password(
                    "A-Strong-Test-Password-2026"
                ),
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
