"""Project integration management API routes."""

from uuid import UUID
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_session
from app.api.project_permissions import (
    require_project_manager,
    require_project_member,
)
from app.core.config import settings
from app.db.session import get_db
from app.models import (
    IntegrationStatus,
    IntegrationType,
    ProjectEnvironment,
    ProjectIntegration,
    ProjectRole,
)
from app.services.github_installation import create_installation_state
from app.schemas.project_operations import (
    IntegrationCreate,
    IntegrationRead,
    IntegrationUpdate,
)

router = APIRouter(
    prefix="/projects/{project_id}/integrations",
    tags=["Project Integrations"],
)


def get_integration_or_404(
    db: Session,
    project_id: UUID,
    integration_id: UUID,
) -> ProjectIntegration:
    """Fetch an integration strictly within its parent project."""

    integration = db.scalar(
        select(ProjectIntegration).where(
            ProjectIntegration.id == integration_id,
            ProjectIntegration.project_id == project_id,
        )
    )

    if integration is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found.",
        )

    return integration


def validate_environment(
    db: Session,
    project_id: UUID,
    environment_id: UUID | None,
) -> None:
    """Ensure an integration references an active environment in its project."""

    if environment_id is None:
        return

    environment = db.scalar(
        select(ProjectEnvironment).where(
            ProjectEnvironment.id == environment_id,
            ProjectEnvironment.project_id == project_id,
        )
    )

    if environment is None or not environment.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Environment must exist, belong to this project, and be active.",
        )


@router.get(
    "",
    response_model=list[IntegrationRead],
    summary="List project integrations",
)
def list_integrations(
    project_id: UUID,
    db: Session = Depends(get_db),
    role: ProjectRole = Depends(require_project_member),
) -> list[ProjectIntegration]:
    """List integrations visible to project members."""

    statement = (
        select(ProjectIntegration)
        .where(ProjectIntegration.project_id == project_id)
        .order_by(ProjectIntegration.created_at.desc())
    )

    return list(db.scalars(statement).all())


@router.post(
    "",
    response_model=IntegrationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a project integration",
)
def create_integration(
    project_id: UUID,
    payload: IntegrationCreate,
    db: Session = Depends(get_db),
    role: ProjectRole = Depends(require_project_manager),
) -> ProjectIntegration:
    """Register an integration in pending state."""

    validate_environment(db, project_id, payload.environment_id)

    integration = ProjectIntegration(
        project_id=project_id,
        integration_type=payload.integration_type,
        name=payload.name,
        environment_id=payload.environment_id,
        external_reference=payload.external_reference or None,
        status=IntegrationStatus.PENDING,
    )

    db.add(integration)
    db.commit()
    db.refresh(integration)

    return integration


@router.patch(
    "/{integration_id}",
    response_model=IntegrationRead,
    summary="Update a project integration",
)
def update_integration(
    project_id: UUID,
    integration_id: UUID,
    payload: IntegrationUpdate,
    db: Session = Depends(get_db),
    role: ProjectRole = Depends(require_project_manager),
) -> ProjectIntegration:
    """Update an integration without allowing cross-project access."""

    integration = get_integration_or_404(
        db,
        project_id,
        integration_id,
    )

    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Provide at least one field to update.",
        )

    if "name" in changes and changes["name"] is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Integration name cannot be null.",
        )

    if "environment_id" in changes:
        validate_environment(
            db,
            project_id,
            changes["environment_id"],
        )

    for field, value in changes.items():
        setattr(integration, field, value)

    db.commit()
    db.refresh(integration)

    return integration


@router.delete(
    "/{integration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect a project integration",
)
def disconnect_integration(
    project_id: UUID,
    integration_id: UUID,
    db: Session = Depends(get_db),
    role: ProjectRole = Depends(require_project_manager),
) -> Response:
    """Disconnect an integration while preserving its history."""

    integration = get_integration_or_404(
        db,
        project_id,
        integration_id,
    )

    integration.status = IntegrationStatus.DISCONNECTED

    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)



@router.post(
    "/{integration_id}/github/install",
    status_code=status.HTTP_200_OK,
    summary="Start GitHub App installation",
)
def start_github_installation(
    project_id: UUID,
    integration_id: UUID,
    db: Session = Depends(get_db),
    role: ProjectRole = Depends(require_project_manager),
    identity: tuple = Depends(get_current_user_session),
) -> dict[str, str | int]:
    """Create a one-time state and return the GitHub App installation URL."""

    user, authenticated_session = identity

    integration = get_integration_or_404(
        db,
        project_id,
        integration_id,
    )

    if integration.integration_type != IntegrationType.GITHUB:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="This integration is not a GitHub integration.",
        )

    if integration.status == IntegrationStatus.CONNECTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This GitHub integration is already connected.",
        )

    if not settings.github_app_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub App integration is not configured on this server.",
        )

    raw_state = create_installation_state(
        db,
        project_id=project_id,
        integration_id=integration.id,
        user_id=user.id,
        session_id=authenticated_session.id,
    )

    db.commit()

    query = urlencode({"state": raw_state})
    authorization_url = (
        f"https://github.com/apps/{settings.GITHUB_APP_SLUG}"
        f"/installations/new?{query}"
    )

    return {
        "authorization_url": authorization_url,
        "expires_in": 600,
    }
