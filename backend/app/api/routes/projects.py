
"""Project management API routes."""

import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import exists, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models import Project, ProjectMember, ProjectRole, User
from app.schemas.project import ProjectCreate, ProjectRead


router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)


def generate_unique_slug(db: Session, name: str) -> str:
    """Generate a URL-friendly slug that does not already exist."""

    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")

    base_slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        ascii_name.casefold(),
    ).strip("-")

    if not base_slug:
        base_slug = "project"

    base_slug = base_slug[:180].rstrip("-")

    candidate = base_slug
    suffix = 2

    while db.scalar(
        select(Project.id).where(Project.slug == candidate)
    ) is not None:
        suffix_text = f"-{suffix}"
        available_length = 180 - len(suffix_text)

        candidate = (
            f"{base_slug[:available_length].rstrip('-')}{suffix_text}"
        )

        suffix += 1

    return candidate


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    """Create a project and assign its creator the owner role."""

    project = Project(
        name=payload.name,
        slug=generate_unique_slug(db, payload.name),
        description=payload.description,
        created_by_id=current_user.id,
    )

    try:
        db.add(project)
        db.flush()

        owner_membership = ProjectMember(
            project_id=project.id,
            user_id=current_user.id,
            role=ProjectRole.OWNER,
        )

        db.add(owner_membership)
        db.commit()
        db.refresh(project)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A project with conflicting data could not be created. Please retry.",
        ) from None

    return project


@router.get(
    "",
    response_model=list[ProjectRead],
    summary="List accessible projects",
)
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Project]:
    """Return projects created by or shared with the authenticated user."""

    is_project_member = exists(
        select(ProjectMember.project_id).where(
            ProjectMember.project_id == Project.id,
            ProjectMember.user_id == current_user.id,
        )
    )

    statement = (
        select(Project)
        .where(
            or_(
                Project.created_by_id == current_user.id,
                is_project_member,
            )
        )
        .order_by(
            Project.updated_at.desc(),
            Project.name.asc(),
        )
    )

    return list(db.scalars(statement).all())
