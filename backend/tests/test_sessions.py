"""Tests for database-backed authentication sessions."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.refresh_tokens import hash_refresh_token
from app.db.base import Base
from app.models import RefreshToken, User, UserSession
from app.services.sessions import (
    SessionCreationError,
    create_user_session,
)


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
def verified_user(db_session):
    user = User(
        full_name="Test Developer",
        email="developer@example.com",
        password_hash="test-password-hash",
        is_active=True,
        email_verified_at=datetime.now(UTC),
    )

    db_session.add(user)
    db_session.commit()

    return user


def test_create_web_session(db_session, verified_user):
    result = create_user_session(
        db_session,
        verified_user,
        client_type="web",
        device_name="Test Browser",
    )

    session = db_session.get(UserSession, result.session_id)

    assert session is not None
    assert session.client_type == "web"
    assert session.device_name == "Test Browser"
    assert session.revoked_at is None

    token_record = db_session.scalar(
        select(RefreshToken).where(RefreshToken.session_id == session.id)
    )

    assert token_record is not None
    assert token_record.token_hash == hash_refresh_token(result.refresh_token)
    assert token_record.token_hash != result.refresh_token


def test_create_mobile_session(db_session, verified_user):
    result = create_user_session(
        db_session,
        verified_user,
        client_type="mobile",
        device_name="Android Device",
    )

    session = db_session.get(UserSession, result.session_id)

    assert session is not None
    assert session.client_type == "mobile"
    assert session.device_name == "Android Device"


def test_session_has_expected_expiry(db_session, verified_user):
    before_creation = datetime.now(UTC)

    result = create_user_session(
        db_session,
        verified_user,
        client_type="web",
    )

    expected_minimum = before_creation + timedelta(days=29)
    expected_maximum = before_creation + timedelta(days=31)

    assert expected_minimum <= result.expires_at <= expected_maximum


@pytest.mark.parametrize(
    "client_type",
    ["desktop", "tablet", "", "WEB"],
)
def test_reject_unsupported_client_type(
    db_session,
    verified_user,
    client_type,
):
    with pytest.raises(SessionCreationError):
        create_user_session(
            db_session,
            verified_user,
            client_type=client_type,
        )

    assert db_session.scalars(select(UserSession)).all() == []


def test_reject_inactive_user(db_session):
    user = User(
        full_name="Inactive Developer",
        email="inactive@example.com",
        password_hash="test-password-hash",
        is_active=False,
        email_verified_at=datetime.now(UTC),
    )

    db_session.add(user)
    db_session.commit()

    with pytest.raises(SessionCreationError):
        create_user_session(
            db_session,
            user,
            client_type="web",
        )

    assert db_session.scalars(select(UserSession)).all() == []


def test_reject_unverified_user(db_session):
    user = User(
        full_name="Unverified Developer",
        email="unverified@example.com",
        password_hash="test-password-hash",
        is_active=True,
        email_verified_at=None,
    )

    db_session.add(user)
    db_session.commit()

    with pytest.raises(SessionCreationError):
        create_user_session(
            db_session,
            user,
            client_type="web",
        )

    assert db_session.scalars(select(UserSession)).all() == []


def test_reject_device_name_too_long(db_session, verified_user):
    with pytest.raises(SessionCreationError):
        create_user_session(
            db_session,
            verified_user,
            client_type="web",
            device_name="D" * 121,
        )

    assert db_session.scalars(select(UserSession)).all() == []


def test_reject_user_agent_too_long(db_session, verified_user):
    with pytest.raises(SessionCreationError):
        create_user_session(
            db_session,
            verified_user,
            client_type="web",
            user_agent="A" * 513,
        )

    assert db_session.scalars(select(UserSession)).all() == []


def test_creates_only_one_initial_refresh_token(
    db_session,
    verified_user,
):
    result = create_user_session(
        db_session,
        verified_user,
        client_type="mobile",
    )

    tokens = db_session.scalars(
        select(RefreshToken).where(RefreshToken.session_id == result.session_id)
    ).all()

    assert len(tokens) == 1
    assert tokens[0].consumed_at is None
    assert tokens[0].revoked_at is None


def test_session_creation_can_be_managed_by_caller(
    db_session,
    verified_user,
):
    result = create_user_session(
        db_session,
        verified_user,
        client_type="web",
        commit=False,
    )

    # The session exists inside the current transaction.
    session = db_session.get(UserSession, result.session_id)
    assert session is not None

    # The caller can roll back the entire operation.
    db_session.rollback()

    # The session must no longer exist after rollback.
    session = db_session.get(UserSession, result.session_id)
    assert session is None

    token = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(result.refresh_token)
        )
    )
    assert token is None
