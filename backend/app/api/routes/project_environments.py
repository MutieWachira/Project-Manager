"""Project environment management API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.project_permissions import (
    require_project_manager,
    require_project_member,
)
from app.db.session import get_db
from app.models import ProjectEnvironment, ProjectRole
from app.schemas.project_operations import (
    EnvironmentCreate,
    EnvironmentRead,
    EnvironmentUpdate,
)

router = APIRouter(
    prefix="/projects/{project_id}/environments",
    tags=["Project Environments"],
)


def get_environment_or_404(
    db: Session,
    project_id: UUID,
    environment_id: UUID,
) -> ProjectEnvironment:
    """Fetch an environment strictly within its parent project."""

    environment = db.scalar(
        select(ProjectEnvironment).where(
            ProjectEnvironment.id == environment_id,
            ProjectEnvironment.project_id == project_id,
        )
    )

    if environment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Environment not found.",
        )

    return environment


@router.get(
    "",
    response_model=list[EnvironmentRead],
    summary="List project environments",
)
def list_environments(
    project_id: UUID,
    db: Session = Depends(get_db),
    role: ProjectRole = Depends(require_project_member),
) -> list[ProjectEnvironment]:
    """List active and inactive environments visible to project members."""

    statement = (
        select(ProjectEnvironment)
        .where(ProjectEnvironment.project_id == project_id)
        .order_by(
            ProjectEnvironment.is_primary.desc(),
            ProjectEnvironment.name.asc(),
        )
    )

    return list(db.scalars(statement).all())


@router.post(
    "",
    response_model=EnvironmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project environment",
)
def create_environment(
    project_id: UUID,
    payload: EnvironmentCreate,
    db: Session = Depends(get_db),
    role: ProjectRole = Depends(require_project_manager),
) -> ProjectEnvironment:
    """Create an environment for a project."""

    if payload.is_primary and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="An inactive environment cannot be primary.",
        )

    environment = ProjectEnvironment(
        project_id=project_id,
        **payload.model_dump(),
    )

    try:
        db.add(environment)
        db.commit()
        db.refresh(environment)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "An environment with that name may already exist, "
                "or the project already has a primary environment."
            ),
        ) from None

    return environment


@router.patch(
    "/{environment_id}",
    response_model=EnvironmentRead,
    summary="Update a project environment",
)
def update_environment(
    project_id: UUID,
    environment_id: UUID,
    payload: EnvironmentUpdate,
    db: Session = Depends(get_db),
    role: ProjectRole = Depends(require_project_manager),
) -> ProjectEnvironment:
    """Update an environment without allowing cross-project access."""

    environment = get_environment_or_404(
        db,
        project_id,
        environment_id,
    )

    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one field to update.",
        )

    required_fields = {
        "name",
        "environment_type",
        "is_primary",
        "is_active",
    }

    for field in required_fields:
        if field in changes and changes[field] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field} cannot be null.",
            )

    next_is_active = changes.get("is_active", environment.is_active)
    next_is_primary = changes.get("is_primary", environment.is_primary)

    if next_is_primary and not next_is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="An inactive environment cannot be primary.",
        )

    for field, value in changes.items():
        setattr(environment, field, value)

    try:
        db.commit()
        db.refresh(environment)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The update conflicts with an existing environment, "
                "possibly because the project already has a primary environment."
            ),
        ) from None

    return environment


@router.delete(
    "/{environment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a project environment",
)
def deactivate_environment(
    project_id: UUID,
    environment_id: UUID,
    db: Session = Depends(get_db),
    role: ProjectRole = Depends(require_project_manager),
) -> Response:
    """Soft-deactivate an environment while preserving its history."""

    environment = get_environment_or_404(
        db,
        project_id,
        environment_id,
    )

    environment.is_active = False
    environment.is_primary = False

    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
