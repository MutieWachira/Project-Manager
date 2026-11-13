"""Tests for refresh-token rotation and replay protection."""

from datetime import UTC, datetime, timedelta

import pytest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.refresh_tokens import hash_refresh_token
from app.db.base import Base
from app.models import RefreshToken, User, UserSession
from app.services.sessions import create_user_session
from app.services.refresh_token_rotation import (
    InvalidRefreshTokenError,
    RefreshTokenReuseError,
    rotate_refresh_token,
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
        full_name="Rotation Test User",
        email="rotation@example.com",
        password_hash="test-password-hash",
        is_active=True,
        email_verified_at=datetime.now(UTC),
    )

    db_session.add(user)
    db_session.commit()

    return user


@pytest.fixture
def session_credentials(db_session, verified_user):
    created = create_user_session(
        db_session,
        verified_user,
        client_type="web",
        device_name="Test Browser",
    )

    return created


def test_successfully_rotates_refresh_token(
    db_session,
    session_credentials,
):
    old_raw_token = session_credentials.refresh_token

    result = rotate_refresh_token(
        db_session,
        old_raw_token,
    )

    assert result.session_id == session_credentials.session_id
    assert result.client_type == "web"
    assert result.refresh_token != old_raw_token
    assert result.expires_at > datetime.now(UTC)

    old_record = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(old_raw_token)
        )
    )

    new_record = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(result.refresh_token)
        )
    )

    assert old_record is not None
    assert old_record.consumed_at is not None
    assert old_record.replaced_by_id == new_record.id

    assert new_record is not None
    assert new_record.consumed_at is None
    assert new_record.revoked_at is None


def test_raw_replacement_token_is_not_stored(
    db_session,
    session_credentials,
):
    result = rotate_refresh_token(
        db_session,
        session_credentials.refresh_token,
    )

    records = db_session.scalars(
        select(RefreshToken).where(RefreshToken.session_id == result.session_id)
    ).all()

    assert len(records) == 2

    for record in records:
        assert record.token_hash != result.refresh_token
        assert len(record.token_hash) == 64


def test_rejects_unknown_refresh_token(db_session):
    with pytest.raises(InvalidRefreshTokenError):
        rotate_refresh_token(
            db_session,
            "unknown-refresh-token",
        )


def test_rejects_expired_refresh_token(
    db_session,
    session_credentials,
):
    token = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash
            == hash_refresh_token(session_credentials.refresh_token)
        )
    )

    token.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    with pytest.raises(InvalidRefreshTokenError):
        rotate_refresh_token(
            db_session,
            session_credentials.refresh_token,
        )


def test_rejects_revoked_refresh_token(
    db_session,
    session_credentials,
):
    token = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash
            == hash_refresh_token(session_credentials.refresh_token)
        )
    )

    token.revoked_at = datetime.now(UTC)
    db_session.commit()

    with pytest.raises(InvalidRefreshTokenError):
        rotate_refresh_token(
            db_session,
            session_credentials.refresh_token,
        )


def test_rejects_expired_session(
    db_session,
    session_credentials,
):
    session = db_session.get(
        UserSession,
        session_credentials.session_id,
    )

    session.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    with pytest.raises(InvalidRefreshTokenError):
        rotate_refresh_token(
            db_session,
            session_credentials.refresh_token,
        )


def test_rejects_revoked_session(
    db_session,
    session_credentials,
):
    session = db_session.get(
        UserSession,
        session_credentials.session_id,
    )

    session.revoked_at = datetime.now(UTC)
    session.revoke_reason = "manual_revocation"
    db_session.commit()

    with pytest.raises(InvalidRefreshTokenError):
        rotate_refresh_token(
            db_session,
            session_credentials.refresh_token,
        )


def test_reuse_of_consumed_token_revokes_entire_session(
    db_session,
    session_credentials,
):
    original_token = session_credentials.refresh_token

    rotate_refresh_token(
        db_session,
        original_token,
    )

    with pytest.raises(RefreshTokenReuseError):
        rotate_refresh_token(
            db_session,
            original_token,
        )

    session = db_session.get(
        UserSession,
        session_credentials.session_id,
    )

    assert session.revoked_at is not None
    assert session.revoke_reason == "refresh_token_reuse"

    records = db_session.scalars(
        select(RefreshToken).where(
            RefreshToken.session_id == session_credentials.session_id
        )
    ).all()

    assert len(records) == 2
    assert all(record.revoked_at is not None for record in records)


def test_inactive_user_cannot_refresh_session(
    db_session,
    verified_user,
    session_credentials,
):
    verified_user.is_active = False
    db_session.commit()

    with pytest.raises(InvalidRefreshTokenError):
        rotate_refresh_token(
            db_session,
            session_credentials.refresh_token,
        )

    session = db_session.get(
        UserSession,
        session_credentials.session_id,
    )

    assert session.revoked_at is not None
    assert session.revoke_reason == "account_not_eligible"


def test_unverified_user_cannot_refresh_session(
    db_session,
    verified_user,
    session_credentials,
):
    verified_user.email_verified_at = None
    db_session.commit()

    with pytest.raises(InvalidRefreshTokenError):
        rotate_refresh_token(
            db_session,
            session_credentials.refresh_token,
        )

    session = db_session.get(
        UserSession,
        session_credentials.session_id,
    )

    assert session.revoked_at is not None
    assert session.revoke_reason == "account_not_eligible"


def test_rejects_web_token_in_mobile_refresh_flow(
    db_session,
    session_credentials,
):
    with pytest.raises(InvalidRefreshTokenError):
        rotate_refresh_token(
            db_session,
            session_credentials.refresh_token,
            expected_client_type="mobile",
        )

    # A mismatched client must not consume or revoke the valid token.
    token = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash
            == hash_refresh_token(session_credentials.refresh_token)
        )
    )

    assert token.consumed_at is None
    assert token.revoked_at is None


def test_rejects_mobile_token_in_web_refresh_flow(
    db_session,
    verified_user,
):
    credentials = create_user_session(
        db_session,
        verified_user,
        client_type="mobile",
        device_name="Test Mobile",
    )

    with pytest.raises(InvalidRefreshTokenError):
        rotate_refresh_token(
            db_session,
            credentials.refresh_token,
            expected_client_type="web",
        )

    token = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(credentials.refresh_token)
        )
    )

    assert token.consumed_at is None
    assert token.revoked_at is None


def test_rotation_returns_client_type(
    db_session,
    verified_user,
):
    credentials = create_user_session(
        db_session,
        verified_user,
        client_type="mobile",
    )

    result = rotate_refresh_token(
        db_session,
        credentials.refresh_token,
        expected_client_type="mobile",
    )

    assert result.client_type == "mobile"
    assert result.session_id == credentials.session_id


def test_rotation_without_expected_client_type_remains_supported(
    db_session,
    session_credentials,
):
    result = rotate_refresh_token(
        db_session,
        session_credentials.refresh_token,
    )

    assert result.client_type == "web"
    assert result.session_id == session_credentials.session_id
