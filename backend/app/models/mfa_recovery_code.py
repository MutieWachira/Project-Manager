"""Database model for single-use MFA recovery codes."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MFARecoveryCode(Base):
    __tablename__ = "mfa_recovery_codes"

    __table_args__ = (
        CheckConstraint(
            "length(code_hash) = 64",
            name="ck_mfa_recovery_codes_hash_length",
        ),
        Index(
            "ix_mfa_recovery_codes_code_hash",
            "code_hash",
            unique=True,
        ),
        Index(
            "ix_mfa_recovery_codes_mfa_id",
            "mfa_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    mfa_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user_mfa.id", ondelete="CASCADE"),
        nullable=False,
    )

    code_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    mfa: Mapped["UserMFA"] = relationship(
        "UserMFA",
        back_populates="recovery_codes",
    )
