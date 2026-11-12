from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ProjectStatus


class Project(Base):
    __tablename__ = "projects"

    __table_args__ = (
        Index("ix_projects_slug", "slug", unique=True),
        Index("ix_projects_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[ProjectStatus] = mapped_column(
        SQLAlchemyEnum(
            ProjectStatus,
            name="project_status",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=ProjectStatus.PLANNED,
        nullable=False,
    )

    created_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    creator: Mapped["User"] = relationship(
        "User",
        back_populates="created_projects",
        foreign_keys=[created_by_id],
    )

    memberships: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan",
    )