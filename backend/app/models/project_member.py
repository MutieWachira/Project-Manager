from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Index,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ProjectRole


class ProjectMember(Base):
    __tablename__ = "project_members"

    __table_args__ = (
        Index("ix_project_members_user_id", "user_id"),
    )

    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    role: Mapped[ProjectRole] = mapped_column(
        SQLAlchemyEnum(
            ProjectRole,
            name="project_role",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=ProjectRole.CONTRIBUTOR,
        nullable=False,
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="memberships",
    )

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="memberships",
    )