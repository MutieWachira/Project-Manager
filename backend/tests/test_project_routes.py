"""Integration tests for project API routes."""

from datetime import UTC, datetime, timedelta
from uuid import UUID
import hashlib
from urllib.parse import parse_qs, urlparse
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import hash_password
from app.core.tokens import create_session_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import (GitHubInstallationState, IntegrationStatus, IntegrationType, Project, ProjectEnvironment, ProjectIntegration, ProjectMember, ProjectRole, User, UserSession)


@pytest.fixture
def api_database():
    """Provide an isolated in-memory database for API tests."""

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

    def override_get_db():
        db = test_session()

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield test_session
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(api_database):
    """Provide a test HTTP client."""

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def authenticated_user(api_database):
    """Create a verified user with a valid database-backed session."""

    with api_database() as db:
        user = User(
            full_name="Project Test User",
            email="project-user@example.com",
            password_hash=hash_password("A-Strong-Test-Password-2026"),
            is_active=True,
            email_verified_at=datetime.now(UTC),
        )

        db.add(user)
        db.flush()

        user_session = UserSession(
            user_id=user.id,
            client_type="web",
            device_name="Project Test Browser",
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )

        db.add(user_session)
        db.commit()

        token = create_session_access_token(
            str(user.id),
            session_id=user_session.id,
        )

        return {
            "id": user.id,
            "token": token,
        }


def test_list_projects_rejects_unauthenticated_user(client):
    response = client.get("/api/v1/projects")

    assert response.status_code == 401


def test_list_projects_returns_projects_created_by_user(
    client,
    api_database,
    authenticated_user,
):
    with api_database() as db:
        project = Project(
            name="My Personal Project",
            slug="my-personal-project",
            description="A project created by the authenticated user.",
            created_by_id=authenticated_user["id"],
        )

        db.add(project)
        db.commit()

        project_id = str(project.id)

    response = client.get(
        "/api/v1/projects",
        headers={
            "Authorization": f"Bearer {authenticated_user['token']}"
        },
    )

    assert response.status_code == 200

    projects = response.json()

    assert len(projects) == 1
    assert projects[0]["id"] == project_id
    assert projects[0]["name"] == "My Personal Project"
    assert projects[0]["slug"] == "my-personal-project"


def test_list_projects_returns_projects_shared_with_user(
    client,
    api_database,
    authenticated_user,
):
    with api_database() as db:
        creator = User(
            full_name="Another Project Owner",
            email="another-owner@example.com",
            password_hash=hash_password("A-Strong-Test-Password-2026"),
            is_active=True,
            email_verified_at=datetime.now(UTC),
        )

        db.add(creator)
        db.flush()

        shared_project = Project(
            name="Shared Project",
            slug="shared-project",
            description="A project shared through membership.",
            created_by_id=creator.id,
        )

        db.add(shared_project)
        db.flush()

        membership = ProjectMember(
            project_id=shared_project.id,
            user_id=authenticated_user["id"],
            role=ProjectRole.VIEWER,
        )

        db.add(membership)
        db.commit()

        shared_project_id = str(shared_project.id)

    response = client.get(
        "/api/v1/projects",
        headers={
            "Authorization": f"Bearer {authenticated_user['token']}"
        },
    )

    assert response.status_code == 200

    projects = response.json()

    assert len(projects) == 1
    assert projects[0]["id"] == shared_project_id
    assert projects[0]["name"] == "Shared Project"


def test_list_projects_does_not_expose_unrelated_projects(
    client,
    api_database,
    authenticated_user,
):
    with api_database() as db:
        unrelated_owner = User(
            full_name="Unrelated Project Owner",
            email="unrelated-owner@example.com",
            password_hash=hash_password("A-Strong-Test-Password-2026"),
            is_active=True,
            email_verified_at=datetime.now(UTC),
        )

        db.add(unrelated_owner)
        db.flush()

        unrelated_project = Project(
            name="Private Project",
            slug="private-project",
            description="This project must not be visible.",
            created_by_id=unrelated_owner.id,
        )

        db.add(unrelated_project)
        db.commit()

    response = client.get(
        "/api/v1/projects",
        headers={
            "Authorization": f"Bearer {authenticated_user['token']}"
        },
    )

    assert response.status_code == 200
    assert response.json() == []


def test_create_project_rejects_unauthenticated_user(client):
    response = client.post(
        "/api/v1/projects",
        json={"name": "My New Project"},
    )

    assert response.status_code == 401


def test_create_project_creates_project_and_owner_membership(
    client,
    api_database,
    authenticated_user,
):
    response = client.post(
        "/api/v1/projects",
        headers={
            "Authorization": f"Bearer {authenticated_user['token']}"
        },
        json={
            "name": "  My New Project  ",
            "description": "  A project created through the API.  ",
        },
    )

    assert response.status_code == 201

    project_data = response.json()

    assert project_data["name"] == "My New Project"
    assert project_data["slug"] == "my-new-project"
    assert project_data["description"] == "A project created through the API."
    assert project_data["status"] == "planned"
    assert project_data["created_by_id"] == str(authenticated_user["id"])

    with api_database() as db:
        project = db.get(Project, UUID(project_data["id"]))

        assert project is not None
        assert project.created_by_id == authenticated_user["id"]

        membership = db.get(
            ProjectMember,
            (project.id, authenticated_user["id"]),
        )

        assert membership is not None
        assert membership.role == ProjectRole.OWNER


def test_create_project_generates_unique_slug_for_duplicate_names(
    client,
    api_database,
    authenticated_user,
):
    with api_database() as db:
        existing_project = Project(
            name="My New Project",
            slug="my-new-project",
            created_by_id=authenticated_user["id"],
        )

        db.add(existing_project)
        db.commit()

    response = client.post(
        "/api/v1/projects",
        headers={
            "Authorization": f"Bearer {authenticated_user['token']}"
        },
        json={"name": "My New Project"},
    )

    assert response.status_code == 201
    assert response.json()["slug"] == "my-new-project-2"


def test_create_project_converts_blank_description_to_none(
    client,
    authenticated_user,
):
    response = client.post(
        "/api/v1/projects",
        headers={
            "Authorization": f"Bearer {authenticated_user['token']}"
        },
        json={
            "name": "Description Test Project",
            "description": "   ",
        },
    )

    assert response.status_code == 201
    assert response.json()["description"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"name": ""},
        {"name": " "},
        {"name": "A"},
        {"name": "   A   "},
    ],
)
def test_create_project_rejects_invalid_names(
    client,
    authenticated_user,
    payload,
):
    response = client.post(
        "/api/v1/projects",
        headers={
            "Authorization": f"Bearer {authenticated_user['token']}"
        },
        json=payload,
    )

    assert response.status_code == 422


def test_create_project_rejects_extra_fields(
    client,
    authenticated_user,
):
    response = client.post(
        "/api/v1/projects",
        headers={
            "Authorization": f"Bearer {authenticated_user['token']}"
        },
        json={
            "name": "Secure Project",
            "created_by_id": "00000000-0000-0000-0000-000000000001",
            "slug": "attacker-controlled-slug",
            "status": "active",
        },
    )

    assert response.status_code == 422


def test_create_project_rejects_oversized_description(
    client,
    authenticated_user,
):
    response = client.post(
        "/api/v1/projects",
        headers={
            "Authorization": f"Bearer {authenticated_user['token']}"
        },
        json={
            "name": "Large Description Project",
            "description": "x" * 2001,
        },
    )

    assert response.status_code == 422

def test_get_project_rejects_unauthenticated_user(
    client,
    api_database,
    authenticated_user,
):
    response = client.get(
        "/api/v1/projects/00000000-0000-0000-0000-000000000001"
    )

    assert response.status_code == 401


def test_get_project_returns_project_to_creator(
    client,
    api_database,
    authenticated_user,
):
    with api_database() as db:
        project = Project(
            name="Project Details Test",
            slug="project-details-test",
            description="Testing project details.",
            created_by_id=authenticated_user["id"],
        )

        db.add(project)
        db.commit()

        project_id = str(project.id)

    response = client.get(
        f"/api/v1/projects/{project_id}",
        headers={
            "Authorization": f"Bearer {authenticated_user['token']}"
        },
    )

    assert response.status_code == 200

    project_data = response.json()

    assert project_data["id"] == project_id
    assert project_data["name"] == "Project Details Test"
    assert project_data["description"] == "Testing project details."
    assert project_data["status"] == "planned"


def test_get_project_returns_project_to_authorized_member(
    client,
    api_database,
    authenticated_user,
):
    with api_database() as db:
        creator = User(
            full_name="Project Creator",
            email="details-creator@example.com",
            password_hash=hash_password("A-Strong-Test-Password-2026"),
            is_active=True,
            email_verified_at=datetime.now(UTC),
        )

        db.add(creator)
        db.flush()

        project = Project(
            name="Shared Details Project",
            slug="shared-details-project",
            created_by_id=creator.id,
        )

        db.add(project)
        db.flush()

        membership = ProjectMember(
            project_id=project.id,
            user_id=authenticated_user["id"],
            role=ProjectRole.VIEWER,
        )

        db.add(membership)
        db.commit()

        project_id = str(project.id)

    response = client.get(
        f"/api/v1/projects/{project_id}",
        headers={
            "Authorization": f"Bearer {authenticated_user['token']}"
        },
    )

    assert response.status_code == 200
    assert response.json()["id"] == project_id


def test_get_project_hides_unrelated_project(
    client,
    api_database,
    authenticated_user,
):
    with api_database() as db:
        creator = User(
            full_name="Unrelated Creator",
            email="details-unrelated@example.com",
            password_hash=hash_password("A-Strong-Test-Password-2026"),
            is_active=True,
            email_verified_at=datetime.now(UTC),
        )

        db.add(creator)
        db.flush()

        project = Project(
            name="Private Details Project",
            slug="private-details-project",
            created_by_id=creator.id,
        )

        db.add(project)
        db.commit()

        project_id = str(project.id)

    response = client.get(
        f"/api/v1/projects/{project_id}",
        headers={
            "Authorization": f"Bearer {authenticated_user['token']}"
        },
    )

    assert response.status_code == 404


def test_get_project_returns_404_for_missing_project(
    client,
    authenticated_user,
):
    response = client.get(
        "/api/v1/projects/00000000-0000-0000-0000-000000000001",
        headers={
            "Authorization": f"Bearer {authenticated_user['token']}"
        },
    )

    assert response.status_code == 404

def _create_project_member(
    db,
    project_id,
    role,
    email="environment-member@example.com",
):
    """Create a project member and return a valid access token."""

    user = User(
        full_name="Environment Test Member",
        email=email,
        password_hash=hash_password("A-Strong-Test-Password-2026"),
        is_active=True,
        email_verified_at=datetime.now(UTC),
    )
    db.add(user)
    db.flush()

    membership = ProjectMember(
        project_id=project_id,
        user_id=user.id,
        role=role,
    )
    db.add(membership)

    user_session = UserSession(
        user_id=user.id,
        client_type="web",
        device_name="Environment Test Browser",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    db.add(user_session)
    db.commit()

    return create_session_access_token(
        str(user.id),
        session_id=user_session.id,
    )


def test_environment_routes_reject_unauthenticated_access(client):
    response = client.get(
        "/api/v1/projects/00000000-0000-0000-0000-000000000001/environments"
    )
    assert response.status_code == 401


def test_owner_can_create_list_update_and_deactivate_environment(
    client,
    api_database,
    authenticated_user,
):
    with api_database() as db:
        project = Project(
            name="Environment Lifecycle Project",
            slug="environment-lifecycle-project",
            created_by_id=authenticated_user["id"],
        )
        db.add(project)
        db.commit()
        project_id = str(project.id)

    headers = {
        "Authorization": f"Bearer {authenticated_user['token']}"
    }
    base = f"/api/v1/projects/{project_id}/environments"

    created = client.post(
        base,
        headers=headers,
        json={
            "name": "Production",
            "environment_type": "production",
            "base_url": "https://example.com",
            "is_primary": True,
        },
    )

    assert created.status_code == 201
    environment = created.json()
    environment_id = environment["id"]
    assert environment["name"] == "Production"
    assert environment["is_primary"] is True

    listed = client.get(base, headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == environment_id

    updated = client.patch(
        f"{base}/{environment_id}",
        headers=headers,
        json={"description": "Live production environment"},
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Live production environment"

    deleted = client.delete(
        f"{base}/{environment_id}",
        headers=headers,
    )
    assert deleted.status_code == 204

    with api_database() as db:
        stored = db.get(ProjectEnvironment, UUID(environment_id))
        assert stored is not None
        assert stored.is_active is False
        assert stored.is_primary is False


def test_viewer_can_list_but_cannot_manage_environments(
    client,
    api_database,
    authenticated_user,
):
    with api_database() as db:
        project = Project(
            name="Viewer Environment Project",
            slug="viewer-environment-project",
            created_by_id=authenticated_user["id"],
        )
        db.add(project)
        db.commit()

        token = _create_project_member(
            db,
            project.id,
            ProjectRole.VIEWER,
        )
        project_id = str(project.id)

    headers = {"Authorization": f"Bearer {token}"}
    base = f"/api/v1/projects/{project_id}/environments"

    listed = client.get(base, headers=headers)
    assert listed.status_code == 200

    created = client.post(
        base,
        headers=headers,
        json={"name": "Viewer Attempt"},
    )
    assert created.status_code == 403


def test_manager_can_create_environment(
    client,
    api_database,
    authenticated_user,
):
    with api_database() as db:
        project = Project(
            name="Manager Environment Project",
            slug="manager-environment-project",
            created_by_id=authenticated_user["id"],
        )
        db.add(project)
        db.commit()

        token = _create_project_member(
            db,
            project.id,
            ProjectRole.MANAGER,
            email="environment-manager@example.com",
        )
        project_id = str(project.id)

    response = client.post(
        f"/api/v1/projects/{project_id}/environments",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Staging", "environment_type": "staging"},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Staging"


def test_environment_creation_rejects_duplicate_names_and_primary(
    client,
    api_database,
    authenticated_user,
):
    with api_database() as db:
        project = Project(
            name="Environment Conflict Project",
            slug="environment-conflict-project",
            created_by_id=authenticated_user["id"],
        )
        db.add(project)
        db.commit()
        project_id = str(project.id)

    headers = {
        "Authorization": f"Bearer {authenticated_user['token']}"
    }
    base = f"/api/v1/projects/{project_id}/environments"

    first = client.post(
        base,
        headers=headers,
        json={"name": "Production", "is_primary": True},
    )
    assert first.status_code == 201

    duplicate_name = client.post(
        base,
        headers=headers,
        json={"name": "Production"},
    )
    assert duplicate_name.status_code == 409

    duplicate_primary = client.post(
        base,
        headers=headers,
        json={"name": "Staging", "is_primary": True},
    )
    assert duplicate_primary.status_code == 409


def test_environment_endpoint_prevents_cross_project_environment_access(
    client,
    api_database,
    authenticated_user,
):
    with api_database() as db:
        first_project = Project(
            name="First Isolation Project",
            slug="first-isolation-project",
            created_by_id=authenticated_user["id"],
        )

        other_owner = User(
            full_name="Other Project Owner",
            email="other-environment-owner@example.com",
            password_hash=hash_password("A-Strong-Test-Password-2026"),
            is_active=True,
            email_verified_at=datetime.now(UTC),
        )
        db.add_all([first_project, other_owner])
        db.flush()

        second_project = Project(
            name="Second Isolation Project",
            slug="second-isolation-project",
            created_by_id=other_owner.id,
        )
        db.add(second_project)
        db.flush()

        foreign_environment = ProjectEnvironment(
            project_id=second_project.id,
            name="Foreign Production",
        )
        db.add(foreign_environment)
        db.commit()

        first_project_id = str(first_project.id)
        foreign_environment_id = str(foreign_environment.id)

    response = client.patch(
        (
            f"/api/v1/projects/{first_project_id}/environments/"
            f"{foreign_environment_id}"
        ),
        headers={
            "Authorization": f"Bearer {authenticated_user['token']}"
        },
        json={"name": "Unauthorized Change"},
    )

    assert response.status_code == 404


def test_inactive_environment_cannot_be_primary(
    client,
    api_database,
    authenticated_user,
):
    with api_database() as db:
        project = Project(
            name="Inactive Primary Test Project",
            slug="inactive-primary-test-project",
            created_by_id=authenticated_user["id"],
        )
        db.add(project)
        db.commit()
        project_id = str(project.id)

    response = client.post(
        f"/api/v1/projects/{project_id}/environments",
        headers={
            "Authorization": f"Bearer {authenticated_user['token']}"
        },
        json={
            "name": "Inactive Production",
            "is_active": False,
            "is_primary": True,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "An inactive environment cannot be primary."
    )


def test_environment_update_rejects_inactive_primary_state(
    client,
    api_database,
    authenticated_user,
):
    with api_database() as db:
        project = Project(
            name="Primary Update Test Project",
            slug="primary-update-test-project",
            created_by_id=authenticated_user["id"],
        )
        db.add(project)
        db.commit()
        project_id = str(project.id)

    headers = {
        "Authorization": f"Bearer {authenticated_user['token']}"
    }
    base = f"/api/v1/projects/{project_id}/environments"

    primary = client.post(
        base,
        headers=headers,
        json={
            "name": "Active Primary",
            "is_primary": True,
        },
    )
    assert primary.status_code == 201
    primary_id = primary.json()["id"]

    inactive = client.post(
        base,
        headers=headers,
        json={
            "name": "Inactive Secondary",
            "is_active": False,
        },
    )
    assert inactive.status_code == 201
    inactive_id = inactive.json()["id"]

    deactivate_primary = client.patch(
        f"{base}/{primary_id}",
        headers=headers,
        json={"is_active": False},
    )
    assert deactivate_primary.status_code == 422

    promote_inactive = client.patch(
        f"{base}/{inactive_id}",
        headers=headers,
        json={"is_primary": True},
    )
    assert promote_inactive.status_code == 422

    with api_database() as db:
        stored_primary = db.get(ProjectEnvironment, UUID(primary_id))
        stored_inactive = db.get(ProjectEnvironment, UUID(inactive_id))

        assert stored_primary.is_active is True
        assert stored_primary.is_primary is True
        assert stored_inactive.is_active is False
        assert stored_inactive.is_primary is False


def test_unrelated_user_cannot_list_project_environments(
    client,
    api_database,
    authenticated_user,
):
    with api_database() as db:
        owner = User(
            full_name="Private Environment Owner",
            email="private-environment-owner@example.com",
            password_hash=hash_password("A-Strong-Test-Password-2026"),
            is_active=True,
            email_verified_at=datetime.now(UTC),
        )
        db.add(owner)
        db.flush()

        project = Project(
            name="Private Environment Project",
            slug="private-environment-project",
            created_by_id=owner.id,
        )
        db.add(project)
        db.commit()
        project_id = str(project.id)

    response = client.get(
        f"/api/v1/projects/{project_id}/environments",
        headers={
            "Authorization": f"Bearer {authenticated_user['token']}"
        },
    )

    assert response.status_code == 404


def test_integration_routes_reject_unauthenticated_access(client):
    response = client.get(
        "/api/v1/projects/"
        "00000000-0000-0000-0000-000000000001/integrations"
    )
    assert response.status_code == 401


def test_owner_can_manage_project_integration(
    client,
    api_database,
    authenticated_user,
):
    with api_database() as db:
        project = Project(
            name="Integration Lifecycle Project",
            slug="integration-lifecycle-project",
            created_by_id=authenticated_user["id"],
        )
        db.add(project)
        db.commit()
        project_id = str(project.id)

    headers = {
        "Authorization": f"Bearer {authenticated_user['token']}"
    }
    base = f"/api/v1/projects/{project_id}/integrations"

    created = client.post(
        base,
        headers=headers,
        json={
            "name": "GitHub Production",
            "integration_type": "github",
            "external_reference": "owner/repository",
        },
    )

    assert created.status_code == 201
    integration = created.json()
    integration_id = integration["id"]

    assert integration["name"] == "GitHub Production"
    assert integration["status"] == "pending"
    assert "configuration" not in integration
    assert "secret_reference" not in integration

    listed = client.get(base, headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    updated = client.patch(
        f"{base}/{integration_id}",
        headers=headers,
        json={"name": "GitHub Main Repository"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "GitHub Main Repository"

    disconnected = client.delete(
        f"{base}/{integration_id}",
        headers=headers,
    )
    assert disconnected.status_code == 204

    from app.models import IntegrationStatus, ProjectIntegration

    with api_database() as db:
        stored = db.get(ProjectIntegration, UUID(integration_id))
        assert stored is not None
        assert stored.status == IntegrationStatus.DISCONNECTED


def test_viewer_can_list_but_cannot_manage_integrations(
    client,
    api_database,
    authenticated_user,
):
    with api_database() as db:
        project = Project(
            name="Viewer Integration Project",
            slug="viewer-integration-project",
            created_by_id=authenticated_user["id"],
        )
        db.add(project)
        db.commit()

        token = _create_project_member(
            db,
            project.id,
            ProjectRole.VIEWER,
            email="integration-viewer@example.com",
        )
        project_id = str(project.id)

    headers = {"Authorization": f"Bearer {token}"}
    base = f"/api/v1/projects/{project_id}/integrations"

    listed = client.get(base, headers=headers)
    assert listed.status_code == 200

    created = client.post(
        base,
        headers=headers,
        json={
            "name": "Viewer Attempt",
            "integration_type": "github",
        },
    )
    assert created.status_code == 403


def test_integration_rejects_foreign_or_inactive_environment(
    client,
    api_database,
    authenticated_user,
):
    with api_database() as db:
        project = Project(
            name="Integration Environment Project",
            slug="integration-environment-project",
            created_by_id=authenticated_user["id"],
        )
        other_owner = User(
            full_name="Other Integration Owner",
            email="other-integration-owner@example.com",
            password_hash=hash_password("A-Strong-Test-Password-2026"),
            is_active=True,
            email_verified_at=datetime.now(UTC),
        )
        db.add_all([project, other_owner])
        db.flush()

        other_project = Project(
            name="Other Integration Project",
            slug="other-integration-project",
            created_by_id=other_owner.id,
        )
        db.add(other_project)
        db.flush()

        foreign_environment = ProjectEnvironment(
            project_id=other_project.id,
            name="Foreign Production",
        )
        inactive_environment = ProjectEnvironment(
            project_id=project.id,
            name="Inactive Staging",
            is_active=False,
        )
        db.add_all([foreign_environment, inactive_environment])
        db.commit()

        project_id = str(project.id)
        foreign_id = str(foreign_environment.id)
        inactive_id = str(inactive_environment.id)

    base = f"/api/v1/projects/{project_id}/integrations"
    headers = {
        "Authorization": f"Bearer {authenticated_user['token']}"
    }

    for environment_id in (foreign_id, inactive_id):
        response = client.post(
            base,
            headers=headers,
            json={
                "name": "Invalid Environment Integration",
                "integration_type": "application",
                "environment_id": environment_id,
            },
        )
        assert response.status_code == 422


def test_unrelated_user_cannot_list_project_integrations(
    client,
    api_database,
    authenticated_user,
):
    with api_database() as db:
        owner = User(
            full_name="Private Integration Owner",
            email="private-integration-owner@example.com",
            password_hash=hash_password("A-Strong-Test-Password-2026"),
            is_active=True,
            email_verified_at=datetime.now(UTC),
        )
        db.add(owner)
        db.flush()

        project = Project(
            name="Private Integration Project",
            slug="private-integration-project",
            created_by_id=owner.id,
        )
        db.add(project)
        db.commit()
        project_id = str(project.id)

    response = client.get(
        f"/api/v1/projects/{project_id}/integrations",
        headers={
            "Authorization": f"Bearer {authenticated_user['token']}"
        },
    )

    assert response.status_code == 404


def test_integration_routes_prevent_cross_project_id_access(
    client,
    api_database,
    authenticated_user,
):
    from app.models import ProjectIntegration

    with api_database() as db:
        first_project = Project(
            name="Integration Isolation First",
            slug="integration-isolation-first",
            created_by_id=authenticated_user["id"],
        )
        other_owner = User(
            full_name="Integration Isolation Owner",
            email="integration-isolation-owner@example.com",
            password_hash=hash_password("A-Strong-Test-Password-2026"),
            is_active=True,
            email_verified_at=datetime.now(UTC),
        )
        db.add_all([first_project, other_owner])
        db.flush()

        second_project = Project(
            name="Integration Isolation Second",
            slug="integration-isolation-second",
            created_by_id=other_owner.id,
        )
        db.add(second_project)
        db.flush()

        foreign_integration = ProjectIntegration(
            project_id=second_project.id,
            integration_type="github",
            name="Private GitHub Integration",
        )
        db.add(foreign_integration)
        db.commit()

        first_project_id = str(first_project.id)
        foreign_integration_id = str(foreign_integration.id)

    response = client.patch(
        (
            f"/api/v1/projects/{first_project_id}/integrations/"
            f"{foreign_integration_id}"
        ),
        headers={
            "Authorization": f"Bearer {authenticated_user['token']}"
        },
        json={"name": "Unauthorized Change"},
    )

    assert response.status_code == 404


def test_integration_create_rejects_status_and_secret_fields(
    client,
    api_database,
    authenticated_user,
):
    with api_database() as db:
        project = Project(
            name="Integration Payload Security",
            slug="integration-payload-security",
            created_by_id=authenticated_user["id"],
        )
        db.add(project)
        db.commit()
        project_id = str(project.id)

    response = client.post(
        f"/api/v1/projects/{project_id}/integrations",
        headers={
            "Authorization": f"Bearer {authenticated_user['token']}"
        },
        json={
            "name": "Untrusted Integration",
            "integration_type": "github",
            "status": "connected",
            "configuration": {"token": "should-not-be-accepted"},
            "secret_reference": "untrusted-secret-reference",
        },
    )

    assert response.status_code == 422


def test_integration_update_rejects_status_and_secret_fields(
    client,
    api_database,
    authenticated_user,
):
    with api_database() as db:
        project = Project(
            name="Integration Update Security",
            slug="integration-update-security",
            created_by_id=authenticated_user["id"],
        )
        db.add(project)
        db.commit()
        project_id = str(project.id)

    headers = {
        "Authorization": f"Bearer {authenticated_user['token']}"
    }
    base = f"/api/v1/projects/{project_id}/integrations"

    created = client.post(
        base,
        headers=headers,
        json={
            "name": "Protected Integration",
            "integration_type": "github",
        },
    )
    assert created.status_code == 201

    integration_id = created.json()["id"]

    response = client.patch(
        f"{base}/{integration_id}",
        headers=headers,
        json={
            "name": "Attempted Escalation",
            "status": "connected",
            "configuration": {"token": "should-not-be-accepted"},
            "secret_reference": "untrusted-secret-reference",
        },
    )

    assert response.status_code == 422



def test_github_installation_start_returns_one_time_url(
    client,
    api_database,
    authenticated_user,
    monkeypatch,
    tmp_path,
):
    key_path = tmp_path / "github-app.pem"
    key_path.write_text("test-only-placeholder", encoding="utf-8")
    key_path.chmod(0o600)

    from pydantic import SecretStr

    monkeypatch.setattr(settings, "GITHUB_APP_ID", "123456")
    monkeypatch.setattr(settings, "GITHUB_APP_SLUG", "test-github-app")
    monkeypatch.setattr(settings, "GITHUB_APP_PRIVATE_KEY_PATH", key_path)
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
        "GITHUB_APP_SETUP_URL",
        "https://example.test/api/v1/github/setup",
    )

    with api_database() as db:
        project = Project(
            name="GitHub Install Project",
            slug="github-install-project",
            created_by_id=authenticated_user["id"],
        )
        db.add(project)
        db.flush()

        integration = ProjectIntegration(
            project_id=project.id,
            integration_type=IntegrationType.GITHUB,
            name="GitHub Repository",
            status=IntegrationStatus.PENDING,
        )
        db.add(integration)
        db.commit()

        project_id = str(project.id)
        integration_id = str(integration.id)

    response = client.post(
        f"/api/v1/projects/{project_id}/integrations/{integration_id}/github/install",
        headers={"Authorization": f"Bearer {authenticated_user['token']}"},
    )

    assert response.status_code == 200
    body = response.json()
    parsed = urlparse(body["authorization_url"])

    assert parsed.scheme == "https"
    assert parsed.netloc == "github.com"
    assert parsed.path == "/apps/test-github-app/installations/new"
    assert body["expires_in"] == 600

    raw_state = parse_qs(parsed.query)["state"][0]
    state_hash = hashlib.sha256(raw_state.encode("utf-8")).hexdigest()

    with api_database() as db:
        state_record = db.query(GitHubInstallationState).filter_by(
            state_hash=state_hash
        ).one()

        assert str(state_record.project_id) == project_id
        assert str(state_record.integration_id) == integration_id
        assert state_record.user_id == authenticated_user["id"]
        assert state_record.consumed_at is None

        stored_integration = db.get(
            ProjectIntegration,
            UUID(integration_id),
        )
        assert stored_integration.status == IntegrationStatus.PENDING


def test_github_installation_start_requires_configuration(
    client,
    api_database,
    authenticated_user,
    monkeypatch,
):
    monkeypatch.setattr(settings, "GITHUB_APP_ID", None)
    monkeypatch.setattr(settings, "GITHUB_APP_SLUG", None)
    monkeypatch.setattr(settings, "GITHUB_APP_PRIVATE_KEY_PATH", None)

    with api_database() as db:
        project = Project(
            name="GitHub Unconfigured Project",
            slug="github-unconfigured-project",
            created_by_id=authenticated_user["id"],
        )
        db.add(project)
        db.flush()

        integration = ProjectIntegration(
            project_id=project.id,
            integration_type=IntegrationType.GITHUB,
            name="GitHub Repository",
            status=IntegrationStatus.PENDING,
        )
        db.add(integration)
        db.commit()

        project_id = str(project.id)
        integration_id = str(integration.id)

    response = client.post(
        f"/api/v1/projects/{project_id}/integrations/{integration_id}/github/install",
        headers={"Authorization": f"Bearer {authenticated_user['token']}"},
    )

    assert response.status_code == 503


def test_github_installation_start_rejects_non_github_integration(
    client,
    api_database,
    authenticated_user,
):
    with api_database() as db:
        project = Project(
            name="Non GitHub Integration Project",
            slug="non-github-install-project",
            created_by_id=authenticated_user["id"],
        )
        db.add(project)
        db.flush()

        integration = ProjectIntegration(
            project_id=project.id,
            integration_type=IntegrationType.APPLICATION,
            name="Application Monitor",
            status=IntegrationStatus.PENDING,
        )
        db.add(integration)
        db.commit()

        project_id = str(project.id)
        integration_id = str(integration.id)

    response = client.post(
        f"/api/v1/projects/{project_id}/integrations/{integration_id}/github/install",
        headers={"Authorization": f"Bearer {authenticated_user['token']}"},
    )

    assert response.status_code == 422


def test_github_installation_start_rejects_unauthenticated_user(client):
    response = client.post(
        "/api/v1/projects/00000000-0000-0000-0000-000000000001/"
        "integrations/00000000-0000-0000-0000-000000000002/github/install"
    )
    assert response.status_code == 401



def test_viewer_cannot_start_github_installation(
    client,
    api_database,
    authenticated_user,
):
    with api_database() as db:
        project = Project(
            name="GitHub Viewer Authorization",
            slug="github-viewer-authorization",
            created_by_id=authenticated_user["id"],
        )
        db.add(project)
        db.flush()

        integration = ProjectIntegration(
            project_id=project.id,
            integration_type=IntegrationType.GITHUB,
            name="GitHub Repository",
            status=IntegrationStatus.PENDING,
        )
        db.add(integration)
        db.flush()

        viewer_token = _create_project_member(
            db,
            project.id,
            ProjectRole.VIEWER,
            email="github-viewer@example.com",
        )

        project_id = str(project.id)
        integration_id = str(integration.id)

    response = client.post(
        f"/api/v1/projects/{project_id}/integrations/{integration_id}/github/install",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )

    assert response.status_code == 403
