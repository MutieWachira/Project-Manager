"""End-to-end tests for the two-stage GitHub App authorization flow."""

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from pydantic import SecretStr

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import (
    GitHubInstallationState,
    IntegrationStatus,
    IntegrationType,
    Project,
    ProjectIntegration,
    ProjectMember,
    ProjectRole,
    User,
    UserSession,
)
from app.services.github_installation import create_installation_state


@pytest.fixture
def flow_context():
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

    def override_get_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with factory() as db:
        user = User(
            full_name="GitHub Flow Owner",
            email="github-flow-owner@example.com",
            password_hash="test-password-hash",
            is_active=True,
            email_verified_at=datetime.now(UTC),
        )
        db.add(user)
        db.flush()

        user_session = UserSession(
            user_id=user.id,
            client_type="web",
            device_name="GitHub Flow Test",
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        db.add(user_session)
        db.flush()

        project = Project(
            name="GitHub Flow Project",
            slug="github-flow-project",
            created_by_id=user.id,
        )
        db.add(project)
        db.flush()

        integration = ProjectIntegration(
            project_id=project.id,
            integration_type=IntegrationType.GITHUB,
            name="GitHub",
            status=IntegrationStatus.PENDING,
        )
        db.add(integration)
        db.commit()

        context = {
            "user_id": user.id,
            "session_id": user_session.id,
            "project_id": project.id,
            "integration_id": integration.id,
        }

    try:
        with TestClient(app) as client:
            yield client, factory, context
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def github_settings(monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_APP_ID", "123456")
    monkeypatch.setattr(settings, "GITHUB_APP_CLIENT_ID", "Iv1.testclient")
    monkeypatch.setattr(
        settings,
        "GITHUB_APP_CLIENT_SECRET",
        SecretStr("test-client-secret"),
    )
    monkeypatch.setattr(
        settings,
        "GITHUB_APP_CALLBACK_URL",
        "https://example.test/api/v1/github/callback",
    )
    monkeypatch.setattr(
        settings,
        "FRONTEND_URL",
        "https://frontend.example.test",
    )


def begin_installation(factory, context):
    with factory() as db:
        raw_state = create_installation_state(
            db,
            project_id=context["project_id"],
            integration_id=context["integration_id"],
            user_id=context["user_id"],
            session_id=context["session_id"],
        )
        db.commit()
    return raw_state


def start_oauth(client, raw_state):
    response = client.get(
        "/api/v1/github/setup",
        params={
            "installation_id": 987654,
            "setup_action": "install",
            "state": raw_state,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    location = urlparse(response.headers["location"])
    assert location.netloc == "github.com"
    assert location.path == "/login/oauth/authorize"

    return parse_qs(location.query)["state"][0]


def test_github_setup_and_callback_complete_successfully(
    flow_context,
    github_settings,
    monkeypatch,
):
    from app.api.routes import github_app

    client, factory, context = flow_context
    raw_state = begin_installation(factory, context)
    oauth_state = start_oauth(client, raw_state)

    monkeypatch.setattr(
        github_app,
        "exchange_github_oauth_code",
        lambda code: "temporary-test-token",
    )
    monkeypatch.setattr(
        github_app,
        "find_user_installation",
        lambda token, installation_id: {
            "id": installation_id,
            "app_id": 123456,
            "account": {"login": "test-owner", "type": "Organization"},
            "repository_selection": "selected",
        },
    )

    response = client.get(
        "/api/v1/github/callback",
        params={"state": oauth_state, "code": "one-time-test-code"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].endswith(
        f"/dashboard/projects/{context['project_id']}?github=connected"
    )

    with factory() as db:
        integration = db.get(ProjectIntegration, context["integration_id"])
        state_record = db.query(GitHubInstallationState).one()

        assert integration.status == IntegrationStatus.CONNECTED
        assert integration.external_reference == "test-owner"
        assert integration.configuration["github_installation_id"] == 987654
        assert integration.configuration["github_account_login"] == "test-owner"
        assert state_record.oauth_consumed_at is not None

        # No OAuth access token is stored in the integration configuration.
        assert "access_token" not in integration.configuration
        assert "temporary-test-token" not in str(integration.configuration)


def test_github_callback_rejects_wrong_app_id(
    flow_context,
    github_settings,
    monkeypatch,
):
    from app.api.routes import github_app

    client, factory, context = flow_context
    oauth_state = start_oauth(
        client,
        begin_installation(factory, context),
    )

    monkeypatch.setattr(
        github_app,
        "exchange_github_oauth_code",
        lambda code: "temporary-test-token",
    )
    monkeypatch.setattr(
        github_app,
        "find_user_installation",
        lambda token, installation_id: {
            "id": installation_id,
            "app_id": 999999,
            "account": {"login": "wrong-app", "type": "Organization"},
        },
    )

    response = client.get(
        "/api/v1/github/callback",
        params={"state": oauth_state, "code": "test-code"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].endswith("?github=error")

    with factory() as db:
        integration = db.get(ProjectIntegration, context["integration_id"])
        assert integration.status == IntegrationStatus.PENDING


def test_github_setup_rejects_revoked_session(
    flow_context,
    github_settings,
):
    client, factory, context = flow_context
    raw_state = begin_installation(factory, context)

    with factory() as db:
        user_session = db.get(UserSession, context["session_id"])
        user_session.revoked_at = datetime.now(UTC)
        db.commit()

    response = client.get(
        "/api/v1/github/setup",
        params={
            "installation_id": 987654,
            "setup_action": "install",
            "state": raw_state,
        },
        follow_redirects=False,
    )

    assert response.status_code == 400

    with factory() as db:
        state_record = db.query(GitHubInstallationState).one()
        assert state_record.consumed_at is not None


def test_github_oauth_callback_state_cannot_be_replayed(
    flow_context,
    github_settings,
    monkeypatch,
):
    from app.api.routes import github_app

    client, factory, context = flow_context
    oauth_state = start_oauth(
        client,
        begin_installation(factory, context),
    )

    monkeypatch.setattr(
        github_app,
        "exchange_github_oauth_code",
        lambda code: "temporary-test-token",
    )
    monkeypatch.setattr(
        github_app,
        "find_user_installation",
        lambda token, installation_id: {
            "id": installation_id,
            "app_id": 123456,
            "account": {"login": "test-owner", "type": "User"},
        },
    )

    first = client.get(
        "/api/v1/github/callback",
        params={"state": oauth_state, "code": "test-code"},
        follow_redirects=False,
    )
    second = client.get(
        "/api/v1/github/callback",
        params={"state": oauth_state, "code": "test-code"},
        follow_redirects=False,
    )

    assert first.status_code == 303
    assert second.status_code == 400


def test_github_callback_rejects_manager_demoted_during_authorization(
    flow_context,
    github_settings,
    monkeypatch,
):
    from app.api.routes import github_app

    client, factory, context = flow_context

    # Transfer project ownership to another user and make the initiator a manager.
    with factory() as db:
        owner = User(
            full_name="Replacement Project Owner",
            email="replacement-owner@example.com",
            password_hash="test-password-hash",
            is_active=True,
            email_verified_at=datetime.now(UTC),
        )
        db.add(owner)
        db.flush()

        project = db.get(Project, context["project_id"])
        project.created_by_id = owner.id

        membership = ProjectMember(
            project_id=project.id,
            user_id=context["user_id"],
            role=ProjectRole.MANAGER,
        )
        db.add(membership)
        db.commit()

    oauth_state = start_oauth(
        client,
        begin_installation(factory, context),
    )

    # Revoke manager privileges after the user has started authorization.
    with factory() as db:
        membership = db.query(ProjectMember).filter_by(
            project_id=context["project_id"],
            user_id=context["user_id"],
        ).one()
        membership.role = ProjectRole.VIEWER
        db.commit()

    monkeypatch.setattr(
        github_app,
        "exchange_github_oauth_code",
        lambda code: pytest.fail("OAuth exchange must not run for a demoted user"),
    )

    response = client.get(
        "/api/v1/github/callback",
        params={"state": oauth_state, "code": "test-code"},
        follow_redirects=False,
    )

    assert response.status_code == 403

    with factory() as db:
        integration = db.get(ProjectIntegration, context["integration_id"])
        assert integration.status == IntegrationStatus.PENDING


def test_github_setup_rejects_unsupported_action(
    flow_context,
    github_settings,
):
    client, factory, context = flow_context
    raw_state = begin_installation(factory, context)

    response = client.get(
        "/api/v1/github/setup",
        params={
            "installation_id": 987654,
            "setup_action": "delete",
            "state": raw_state,
        },
        follow_redirects=False,
    )

    assert response.status_code == 400

    # Unsupported actions are rejected before consuming the valid state.
    with factory() as db:
        state_record = db.query(GitHubInstallationState).one()
        assert state_record.consumed_at is None


def test_github_callback_handles_user_denial(
    flow_context,
    github_settings,
):
    client, factory, context = flow_context
    oauth_state = start_oauth(
        client,
        begin_installation(factory, context),
    )

    response = client.get(
        "/api/v1/github/callback",
        params={
            "state": oauth_state,
            "error": "access_denied",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].endswith("?github=error")

    with factory() as db:
        integration = db.get(ProjectIntegration, context["integration_id"])
        state_record = db.query(GitHubInstallationState).one()

        assert integration.status == IntegrationStatus.PENDING
        assert state_record.oauth_consumed_at is not None
