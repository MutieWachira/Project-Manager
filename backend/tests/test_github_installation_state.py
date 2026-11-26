"""Tests for secure GitHub App installation state handling."""

import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import (
    GitHubInstallationState,
    IntegrationType,
    Project,
    ProjectIntegration,
    User,
    UserSession,
)
from app.services.github_installation import (
    create_installation_state,
    consume_installation_state,
)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    factory = sessionmaker(
        bind=engine,
        class_=Session,
        expire_on_commit=False,
    )
    db = factory()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def installation_context(db_session):
    user = User(
        full_name="GitHub Test Owner",
        email="github-owner@example.com",
        password_hash="test-password-hash",
        is_active=True,
        email_verified_at=datetime.now(UTC),
    )
    db_session.add(user)
    db_session.flush()

    user_session = UserSession(
        user_id=user.id,
        client_type="web",
        device_name="GitHub Test Browser",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    db_session.add(user_session)
    db_session.flush()

    project = Project(
        name="GitHub Integration Test",
        slug="github-integration-test",
        created_by_id=user.id,
    )
    db_session.add(project)
    db_session.flush()

    integration = ProjectIntegration(
        project_id=project.id,
        integration_type=IntegrationType.GITHUB,
        name="GitHub",
    )
    db_session.add(integration)
    db_session.commit()

    return {
        "user": user,
        "session": user_session,
        "project": project,
        "integration": integration,
    }


def create_state(db_session, context):
    return create_installation_state(
        db_session,
        project_id=context["project"].id,
        integration_id=context["integration"].id,
        user_id=context["user"].id,
        session_id=context["session"].id,
    )


def test_state_stores_hash_not_raw_value(db_session, installation_context):
    raw_state = create_state(db_session, installation_context)

    record = db_session.scalar(
        select(GitHubInstallationState).where(
            GitHubInstallationState.project_id
            == installation_context["project"].id
        )
    )

    assert record is not None
    assert record.state_hash == hashlib.sha256(
        raw_state.encode("utf-8")
    ).hexdigest()
    assert record.state_hash != raw_state
    assert record.consumed_at is None

    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)

    assert expires_at > datetime.now(UTC)


def test_valid_state_can_be_consumed_once(
    db_session,
    installation_context,
):
    raw_state = create_state(db_session, installation_context)

    result = consume_installation_state(
        db_session,
        raw_state,
        user_id=installation_context["user"].id,
        session_id=installation_context["session"].id,
    )
    db_session.commit()

    assert result is not None
    assert result.project_id == installation_context["project"].id
    assert result.integration_id == installation_context["integration"].id
    assert result.consumed_at is not None

    replay = consume_installation_state(
        db_session,
        raw_state,
        user_id=installation_context["user"].id,
        session_id=installation_context["session"].id,
    )

    assert replay is None


def test_state_rejects_different_user(
    db_session,
    installation_context,
):
    raw_state = create_state(db_session, installation_context)

    result = consume_installation_state(
        db_session,
        raw_state,
        user_id=__import__("uuid").uuid4(),
        session_id=installation_context["session"].id,
    )

    assert result is None


def test_state_rejects_different_session(
    db_session,
    installation_context,
):
    raw_state = create_state(db_session, installation_context)

    result = consume_installation_state(
        db_session,
        raw_state,
        user_id=installation_context["user"].id,
        session_id=__import__("uuid").uuid4(),
    )

    assert result is None


def test_expired_state_cannot_be_consumed(
    db_session,
    installation_context,
):
    raw_state = create_state(db_session, installation_context)
    record = db_session.scalar(
        select(GitHubInstallationState).where(
            GitHubInstallationState.state_hash
            == hashlib.sha256(raw_state.encode("utf-8")).hexdigest()
        )
    )
    record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()

    result = consume_installation_state(
        db_session,
        raw_state,
        user_id=installation_context["user"].id,
        session_id=installation_context["session"].id,
    )

    assert result is None


@pytest.mark.parametrize("raw_state", ["", "x" * 257])
def test_invalid_state_input_is_rejected(
    db_session,
    installation_context,
    raw_state,
):
    result = consume_installation_state(
        db_session,
        raw_state,
        user_id=installation_context["user"].id,
        session_id=installation_context["session"].id,
    )

    assert result is None
