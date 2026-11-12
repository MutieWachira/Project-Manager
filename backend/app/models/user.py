
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        Index("ix_users_email", "email", unique=True),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    created_projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="creator",
        foreign_keys="Project.created_by_id",
    )

    memberships: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    email_verification_tokens: Mapped[list["EmailVerificationToken"]] = relationship(
        "EmailVerificationToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
