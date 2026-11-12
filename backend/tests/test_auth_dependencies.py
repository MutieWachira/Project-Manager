from datetime import UTC, datetime

import pytest

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.core.security import hash_password
from app.core.tokens import create_access_token
from app.db.base import Base
from app.models import User


@pytest.fixture
def db_session():
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

    db = test_session()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def active_user(db_session):
    user = User(
        full_name="Test Developer",
        email="developer@example.com",
        password_hash=hash_password(
            "A-Strong-Test-Password-2026"
        ),
        is_active=True,
        email_verified_at=datetime.now(UTC),
    )

    db_session.add(user)
    db_session.commit()

    return user


def test_dependency_returns_authenticated_user(
    db_session,
    active_user,
):
    token = create_access_token(str(active_user.id))

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )

    result = get_current_user(
        credentials=credentials,
        db=db_session,
    )

    assert result.id == active_user.id
    assert result.email == active_user.email


def test_dependency_rejects_missing_credentials(db_session):
    with pytest.raises(HTTPException) as exc:
        get_current_user(
            credentials=None,
            db=db_session,
        )

    assert exc.value.status_code == 401


def test_dependency_rejects_invalid_token(db_session):
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="invalid-token",
    )

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            credentials=credentials,
            db=db_session,
        )

    assert exc.value.status_code == 401


def test_dependency_rejects_deleted_user(db_session):
    from uuid import uuid4

    token = create_access_token(str(uuid4()))

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            credentials=credentials,
            db=db_session,
        )

    assert exc.value.status_code == 401


def test_dependency_rejects_inactive_user(db_session):
    active_user = User(
        full_name="Inactive Developer",
        email="inactive@example.com",
        password_hash=hash_password(
            "A-Strong-Test-Password-2026"
        ),
        is_active=False,
        email_verified_at=datetime.now(UTC),
    )

    db_session.add(active_user)
    db_session.commit()

    token = create_access_token(str(active_user.id))

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            credentials=credentials,
            db=db_session,
        )

    assert exc.value.status_code == 401