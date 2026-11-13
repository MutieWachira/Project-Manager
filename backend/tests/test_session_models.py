from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import RefreshToken, User, UserSession


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        yield session

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def test_user(db_session):
    user = User(
        full_name="Test User",
        email="session-test@example.com",
        password_hash="test-password-hash",
        is_active=True,
        email_verified_at=datetime.now(UTC),
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


def test_create_web_session(db_session, test_user):
    session = UserSession(
        user_id=test_user.id,
        client_type="web",
        device_name="Test Browser",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    assert session.id is not None
    assert session.user_id == test_user.id
    assert session.client_type == "web"
    assert session.revoked_at is None


def test_create_mobile_session(db_session, test_user):
    session = UserSession(
        user_id=test_user.id,
        client_type="mobile",
        device_name="Test Phone",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    db_session.add(session)
    db_session.commit()

    assert session.client_type == "mobile"


def test_reject_invalid_client_type(db_session, test_user):
    session = UserSession(
        user_id=test_user.id,
        client_type="desktop",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    db_session.add(session)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_create_refresh_token(db_session, test_user):
    user_session = UserSession(
        user_id=test_user.id,
        client_type="web",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    db_session.add(user_session)
    db_session.flush()

    refresh_token = RefreshToken(
        session_id=user_session.id,
        token_hash="a" * 64,
        expires_at=user_session.expires_at,
    )

    db_session.add(refresh_token)
    db_session.commit()

    assert refresh_token.id is not None
    assert refresh_token.session_id == user_session.id
    assert len(refresh_token.token_hash) == 64


def test_refresh_token_hash_must_be_64_characters(db_session, test_user):
    user_session = UserSession(
        user_id=test_user.id,
        client_type="mobile",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    db_session.add(user_session)
    db_session.flush()

    token = RefreshToken(
        session_id=user_session.id,
        token_hash="too-short",
        expires_at=user_session.expires_at,
    )

    db_session.add(token)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_refresh_token_hash_must_be_unique(db_session, test_user):
    user_session = UserSession(
        user_id=test_user.id,
        client_type="web",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    db_session.add(user_session)
    db_session.flush()

    expires_at = datetime.now(UTC) + timedelta(days=30)
    token_hash = "b" * 64

    first = RefreshToken(
        session_id=user_session.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )

    second = RefreshToken(
        session_id=user_session.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )

    db_session.add_all([first, second])

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_user_session_relationship(db_session, test_user):
    user_session = UserSession(
        client_type="web",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    test_user.sessions.append(user_session)
    db_session.commit()

    assert user_session.user.id == test_user.id
    assert user_session in test_user.sessions


def test_refresh_token_replacement_relationship(db_session, test_user):
    user_session = UserSession(
        user_id=test_user.id,
        client_type="mobile",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    db_session.add(user_session)
    db_session.flush()

    old_token = RefreshToken(
        session_id=user_session.id,
        token_hash="c" * 64,
        expires_at=user_session.expires_at,
        consumed_at=datetime.now(UTC),
    )

    new_token = RefreshToken(
        session_id=user_session.id,
        token_hash="d" * 64,
        expires_at=user_session.expires_at,
    )

    db_session.add_all([old_token, new_token])
    db_session.flush()

    old_token.replaced_by_id = new_token.id
    db_session.commit()

    db_session.refresh(old_token)

    assert old_token.replaced_by.id == new_token.id
