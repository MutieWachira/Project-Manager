import pytest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import verify_password
from app.db.base import Base
from app.models import EmailVerificationToken, User
from app.schemas.auth import RegisterRequest
from app.services import authentication


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
def registration():
    return RegisterRequest(
        full_name="Test Developer",
        email="developer@example.com",
        password="A-Strong-Test-Password-2026",
    )


def test_register_creates_unverified_user(
    db_session,
    registration,
    monkeypatch,
):
    captured_emails = []

    def fake_send_email(**kwargs):
        captured_emails.append(kwargs)

    monkeypatch.setattr(
        authentication,
        "send_email_verification_email",
        fake_send_email,
    )

    authentication.register_user(db_session, registration)

    user = db_session.scalar(select(User).where(User.email == registration.email))

    assert user is not None
    assert user.full_name == "Test Developer"
    assert user.is_active is True
    assert user.email_verified_at is None

    assert verify_password(
        registration.password,
        user.password_hash,
    )

    assert len(captured_emails) == 1
    assert captured_emails[0]["recipient_email"] == registration.email


def test_register_stores_only_hashed_verification_token(
    db_session,
    registration,
    monkeypatch,
):
    captured_emails = []

    def fake_send_email(**kwargs):
        captured_emails.append(kwargs)

    monkeypatch.setattr(
        authentication,
        "send_email_verification_email",
        fake_send_email,
    )

    authentication.register_user(db_session, registration)

    user = db_session.scalar(select(User).where(User.email == registration.email))

    token_record = db_session.scalar(
        select(EmailVerificationToken).where(EmailVerificationToken.user_id == user.id)
    )

    raw_token = captured_emails[0]["token"]

    assert token_record is not None
    assert token_record.token_hash != raw_token
    assert len(token_record.token_hash) == 64


def test_duplicate_registration_does_not_send_another_email(
    db_session,
    registration,
    monkeypatch,
):
    email_calls = []

    monkeypatch.setattr(
        authentication,
        "send_email_verification_email",
        lambda **kwargs: email_calls.append(kwargs),
    )

    authentication.register_user(db_session, registration)
    authentication.register_user(db_session, registration)

    users = db_session.scalars(select(User)).all()

    assert len(users) == 1
    assert len(email_calls) == 1


def test_email_delivery_failure_keeps_account_unverified(
    db_session,
    registration,
    monkeypatch,
):
    def fail_to_send_email(**kwargs):
        raise authentication.EmailDeliveryError("Simulated SMTP failure.")

    monkeypatch.setattr(
        authentication,
        "send_email_verification_email",
        fail_to_send_email,
    )

    authentication.register_user(db_session, registration)

    user = db_session.scalar(select(User).where(User.email == registration.email))

    assert user is not None
    assert user.email_verified_at is None

    token_record = db_session.scalar(
        select(EmailVerificationToken).where(EmailVerificationToken.user_id == user.id)
    )

    assert token_record is not None


def test_database_failure_rolls_back_registration(
    db_session,
    registration,
    monkeypatch,
):
    def fail_to_create_token(*args, **kwargs):
        raise RuntimeError("Simulated token creation failure.")

    monkeypatch.setattr(
        authentication,
        "create_email_verification_token",
        fail_to_create_token,
    )

    with pytest.raises(RuntimeError):
        authentication.register_user(db_session, registration)

    user = db_session.scalar(select(User).where(User.email == registration.email))

    assert user is None
