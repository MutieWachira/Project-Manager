import pytest

from datetime import UTC, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.models import User
from app.schemas.auth import LoginRequest
from app.services.authentication import authenticate_user


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
        password_hash=hash_password("A-Strong-Test-Password-2026"),
        is_active=True,
        email_verified_at=datetime.now(UTC),
    )

    db_session.add(user)
    db_session.commit()

    return user


def test_login_returns_authenticated_user(
    db_session,
    verified_user,
):
    credentials = LoginRequest(
        email="developer@example.com",
        password="A-Strong-Test-Password-2026",
    )

    user = authenticate_user(db_session, credentials)

    assert user is not None
    assert user.id == verified_user.id
    assert user.email == "developer@example.com"


def test_login_rejects_unknown_email(db_session):
    credentials = LoginRequest(
        email="unknown@example.com",
        password="A-Strong-Test-Password-2026",
    )

    assert authenticate_user(db_session, credentials) is None


def test_login_rejects_wrong_password(
    db_session,
    verified_user,
):
    credentials = LoginRequest(
        email="developer@example.com",
        password="Wrong-Password-2026",
    )

    assert authenticate_user(db_session, credentials) is None


def test_login_rejects_unverified_email(db_session):
    user = User(
        full_name="Unverified Developer",
        email="unverified@example.com",
        password_hash=hash_password("A-Strong-Test-Password-2026"),
        is_active=True,
        email_verified_at=None,
    )

    db_session.add(user)
    db_session.commit()

    credentials = LoginRequest(
        email="unverified@example.com",
        password="A-Strong-Test-Password-2026",
    )

    assert authenticate_user(db_session, credentials) is None


def test_login_rejects_inactive_account(db_session):
    user = User(
        full_name="Inactive Developer",
        email="inactive@example.com",
        password_hash=hash_password("A-Strong-Test-Password-2026"),
        is_active=False,
        email_verified_at=datetime.now(UTC),
    )

    db_session.add(user)
    db_session.commit()

    credentials = LoginRequest(
        email="inactive@example.com",
        password="A-Strong-Test-Password-2026",
    )

    assert authenticate_user(db_session, credentials) is None
