"""Integration tests for project API routes."""

from datetime import UTC, datetime, timedelta
from uuid import UUID
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.core.tokens import create_session_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Project, ProjectMember, ProjectRole, User, UserSession


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
