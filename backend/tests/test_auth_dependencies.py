"""Tests for session-aware authentication dependencies."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.core.security import hash_password
from app.core.tokens import (
    create_access_token,
    create_session_access_token,
)
from app.db.base import Base
from app.models import User, UserSession


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
        password_hash=hash_password("A-Strong-Test-Password-2026"),
        is_active=True,
        email_verified_at=datetime.now(UTC),
    )

    db_session.add(user)
    db_session.commit()

    return user


@pytest.fixture
def active_session(db_session, active_user):
    authenticated_session = UserSession(
        user_id=active_user.id,
        client_type="web",
        device_name="Test Browser",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    db_session.add(authenticated_session)
    db_session.commit()

    return authenticated_session


def make_credentials(token: str):
    return HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )


def make_session_token(user, authenticated_session):
    return create_session_access_token(
        str(user.id),
        session_id=authenticated_session.id,
    )


def test_dependency_returns_authenticated_user(
    db_session,
    active_user,
    active_session,
):
    credentials = make_credentials(make_session_token(active_user, active_session))

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
    with pytest.raises(HTTPException) as exc:
        get_current_user(
            credentials=make_credentials("invalid-token"),
            db=db_session,
        )

    assert exc.value.status_code == 401


def test_dependency_rejects_legacy_token(
    db_session,
    active_user,
):
    token = create_access_token(str(active_user.id))

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            credentials=make_credentials(token),
            db=db_session,
        )

    assert exc.value.status_code == 401


def test_dependency_rejects_deleted_user(db_session):
    token = create_session_access_token(
        str(uuid4()),
        session_id=uuid4(),
    )

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            credentials=make_credentials(token),
            db=db_session,
        )

    assert exc.value.status_code == 401


def test_dependency_rejects_inactive_user(
    db_session,
    active_session,
):
    user = User(
        full_name="Inactive Developer",
        email="inactive@example.com",
        password_hash=hash_password("A-Strong-Test-Password-2026"),
        is_active=False,
        email_verified_at=datetime.now(UTC),
    )

    db_session.add(user)
    db_session.commit()

    token = create_session_access_token(
        str(user.id),
        session_id=active_session.id,
    )

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            credentials=make_credentials(token),
            db=db_session,
        )

    assert exc.value.status_code == 401


def test_dependency_rejects_unverified_user(db_session):
    user = User(
        full_name="Unverified Developer",
        email="unverified@example.com",
        password_hash=hash_password("A-Strong-Test-Password-2026"),
        is_active=True,
        email_verified_at=None,
    )

    db_session.add(user)
    db_session.flush()

    authenticated_session = UserSession(
        user_id=user.id,
        client_type="web",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    db_session.add(authenticated_session)
    db_session.commit()

    token = make_session_token(user, authenticated_session)

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            credentials=make_credentials(token),
            db=db_session,
        )

    assert exc.value.status_code == 401


def test_dependency_rejects_missing_session(
    db_session,
    active_user,
):
    token = create_session_access_token(
        str(active_user.id),
        session_id=uuid4(),
    )

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            credentials=make_credentials(token),
            db=db_session,
        )

    assert exc.value.status_code == 401


def test_dependency_rejects_session_belonging_to_another_user(
    db_session,
    active_user,
    active_session,
):
    another_user = User(
        full_name="Another Developer",
        email="another@example.com",
        password_hash=hash_password("A-Strong-Test-Password-2026"),
        is_active=True,
        email_verified_at=datetime.now(UTC),
    )

    db_session.add(another_user)
    db_session.commit()

    token = create_session_access_token(
        str(another_user.id),
        session_id=active_session.id,
    )

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            credentials=make_credentials(token),
            db=db_session,
        )

    assert exc.value.status_code == 401


def test_dependency_rejects_revoked_session(
    db_session,
    active_user,
    active_session,
):
    active_session.revoked_at = datetime.now(UTC)
    db_session.commit()

    token = make_session_token(active_user, active_session)

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            credentials=make_credentials(token),
            db=db_session,
        )

    assert exc.value.status_code == 401


def test_dependency_rejects_expired_session(
    db_session,
    active_user,
    active_session,
):
    active_session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()

    token = make_session_token(active_user, active_session)

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            credentials=make_credentials(token),
            db=db_session,
        )

    assert exc.value.status_code == 401
