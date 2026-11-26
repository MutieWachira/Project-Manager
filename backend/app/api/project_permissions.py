"""Project-scoped authorization dependencies."""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models import Project, ProjectMember, ProjectRole, User


def require_project_member(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectRole:
    """Require project membership, treating the creator as its owner."""

    project = db.scalar(
        select(Project).where(Project.id == project_id)
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    if project.created_by_id == current_user.id:
        return ProjectRole.OWNER

    membership = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.id,
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    return membership.role


def require_project_manager(
    role: ProjectRole = Depends(require_project_member),
) -> ProjectRole:
    """Require owner or manager permissions for project mutations."""

    if role not in (ProjectRole.OWNER, ProjectRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this project.",
        )

    return role
