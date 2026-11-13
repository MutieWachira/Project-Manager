"""Tests for MFA database models and relationships."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import MFARecoveryCode, User, UserMFA


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


def test_create_pending_mfa_enrollment(db_session, verified_user):
    mfa = UserMFA(
        user_id=verified_user.id,
        pending_secret="encrypted-pending-secret",
        is_enabled=False,
    )

    db_session.add(mfa)
    db_session.commit()

    saved = db_session.scalar(
        select(UserMFA).where(UserMFA.user_id == verified_user.id)
    )

    assert saved is not None
    assert saved.pending_secret == "encrypted-pending-secret"
    assert saved.encrypted_secret is None
    assert saved.is_enabled is False


def test_user_has_one_mfa_configuration(db_session, verified_user):
    first = UserMFA(user_id=verified_user.id)
    second = UserMFA(user_id=verified_user.id)

    db_session.add_all([first, second])

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_enabled_mfa_requires_confirmed_secret(
    db_session,
    verified_user,
):
    mfa = UserMFA(
        user_id=verified_user.id,
        is_enabled=True,
    )

    db_session.add(mfa)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_enabled_mfa_cannot_have_pending_secret(
    db_session,
    verified_user,
):
    mfa = UserMFA(
        user_id=verified_user.id,
        encrypted_secret="encrypted-active-secret",
        pending_secret="encrypted-pending-secret",
        is_enabled=True,
        confirmed_at=datetime.now(UTC),
    )

    db_session.add(mfa)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_create_mfa_recovery_code(db_session, verified_user):
    mfa = UserMFA(user_id=verified_user.id)

    recovery_code = MFARecoveryCode(
        mfa=mfa,
        code_hash="a" * 64,
    )

    db_session.add(mfa)
    db_session.add(recovery_code)
    db_session.commit()

    saved = db_session.scalar(
        select(MFARecoveryCode).where(MFARecoveryCode.code_hash == "a" * 64)
    )

    assert saved is not None
    assert saved.used_at is None
    assert saved.mfa_id == mfa.id


def test_recovery_code_hash_must_have_64_characters(
    db_session,
    verified_user,
):
    mfa = UserMFA(user_id=verified_user.id)

    db_session.add(
        MFARecoveryCode(
            mfa=mfa,
            code_hash="too-short",
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_user_mfa_relationship(db_session, verified_user):
    mfa = UserMFA(
        pending_secret="encrypted-pending-secret",
    )

    verified_user.mfa = mfa

    db_session.commit()

    assert verified_user.mfa is not None
    assert verified_user.mfa.user_id == verified_user.id


def test_recovery_code_relationship(db_session, verified_user):
    mfa = UserMFA()
    verified_user.mfa = mfa

    mfa.recovery_codes.append(MFARecoveryCode(code_hash="b" * 64))

    db_session.commit()

    assert len(mfa.recovery_codes) == 1
    assert mfa.recovery_codes[0].mfa_id == mfa.id


def test_create_mfa_login_challenge(db_session, verified_user):
    from datetime import timedelta

    from app.models import MFALoginChallenge

    now = datetime.now(UTC)

    challenge = MFALoginChallenge(
        user_id=verified_user.id,
        created_at=now,
        expires_at=now + timedelta(minutes=5),
    )

    db_session.add(challenge)
    db_session.commit()

    saved = db_session.get(MFALoginChallenge, challenge.id)

    assert saved is not None
    assert saved.user_id == verified_user.id
    assert saved.failed_attempts == 0
    assert saved.consumed_at is None
    assert saved.revoked_at is None


def test_mfa_login_challenge_user_relationship(
    db_session,
    verified_user,
):
    from datetime import timedelta

    from app.models import MFALoginChallenge

    now = datetime.now(UTC)

    challenge = MFALoginChallenge(
        expires_at=now + timedelta(minutes=5),
    )

    verified_user.mfa_login_challenges.append(challenge)
    db_session.commit()

    assert len(verified_user.mfa_login_challenges) == 1
    assert challenge.user_id == verified_user.id
    assert challenge.user.id == verified_user.id


def test_mfa_login_challenge_can_be_consumed_and_revoked(
    db_session,
    verified_user,
):
    from datetime import timedelta

    from app.models import MFALoginChallenge

    now = datetime.now(UTC)

    challenge = MFALoginChallenge(
        user_id=verified_user.id,
        created_at=now,
        expires_at=now + timedelta(minutes=5),
    )

    db_session.add(challenge)
    db_session.commit()

    challenge.consumed_at = now
    challenge.revoked_at = now

    db_session.commit()
    db_session.refresh(challenge)

    assert challenge.consumed_at is not None
    assert challenge.revoked_at is not None

    assert challenge.consumed_at.replace(tzinfo=UTC) == now
    assert challenge.revoked_at.replace(tzinfo=UTC) == now


def test_mfa_login_challenge_rejects_negative_failed_attempts(
    db_session,
    verified_user,
):
    from datetime import timedelta

    from app.models import MFALoginChallenge

    now = datetime.now(UTC)

    challenge = MFALoginChallenge(
        user_id=verified_user.id,
        created_at=now,
        expires_at=now + timedelta(minutes=5),
        failed_attempts=-1,
    )

    db_session.add(challenge)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_mfa_login_challenge_expiry_must_follow_creation(
    db_session,
    verified_user,
):
    from datetime import timedelta

    from app.models import MFALoginChallenge

    now = datetime.now(UTC)

    challenge = MFALoginChallenge(
        user_id=verified_user.id,
        created_at=now,
        expires_at=now - timedelta(minutes=1),
    )

    db_session.add(challenge)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_deleting_user_cascades_to_mfa_login_challenges(
    db_session,
    verified_user,
):
    from datetime import timedelta

    from sqlalchemy import select

    from app.models import MFALoginChallenge

    now = datetime.now(UTC)

    challenge = MFALoginChallenge(
        expires_at=now + timedelta(minutes=5),
    )

    verified_user.mfa_login_challenges.append(challenge)
    db_session.commit()

    challenge_id = challenge.id

    db_session.delete(verified_user)
    db_session.commit()

    saved = db_session.scalar(
        select(MFALoginChallenge).where(MFALoginChallenge.id == challenge_id)
    )

    assert saved is None
