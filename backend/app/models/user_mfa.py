"""Database model for user multi-factor authentication settings."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.mfa_recovery_code import MFARecoveryCode
    from app.models.user import User


class UserMFA(Base):
    __tablename__ = "user_mfa"

    __table_args__ = (
        CheckConstraint(
            "is_enabled = false OR "
            "(encrypted_secret IS NOT NULL AND confirmed_at IS NOT NULL)",
            name="ck_user_mfa_enabled_has_confirmed_secret",
        ),
        CheckConstraint(
            "is_enabled = false OR pending_secret IS NULL",
            name="ck_user_mfa_enabled_has_no_pending_secret",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    encrypted_secret: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    pending_secret: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    pending_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_totp_counter: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    confirmed_at: Mapped[datetime | None] = mapped_column(
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

    user: Mapped[User] = relationship(
        "User",
        back_populates="mfa",
    )

    recovery_codes: Mapped[list[MFARecoveryCode]] = relationship(
        "MFARecoveryCode",
        back_populates="mfa",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
