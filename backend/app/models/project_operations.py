"""Operational models for project environments, integrations, events and incidents."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import (
    EnvironmentType,
    EventSeverity,
    IncidentStatus,
    IntegrationStatus,
    IntegrationType,
)


def enum_values(enum_class):
    return [item.value for item in enum_class]


class ProjectEnvironment(Base):
    __tablename__ = "project_environments"

    __table_args__ = (
        CheckConstraint(
            "NOT is_primary OR is_active",
            name="ck_project_environments_primary_requires_active",
        ),
        UniqueConstraint(
            "project_id",
            "name",
            name="uq_project_environments_project_name",
        ),
        Index(
            "uq_project_environments_primary",
            "project_id",
            unique=True,
            postgresql_where=text("is_primary = true"),
            sqlite_where=text("is_primary = 1"),
        ),
        Index("ix_project_environments_project_id", "project_id"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    environment_type: Mapped[EnvironmentType] = mapped_column(
        SQLAlchemyEnum(
            EnvironmentType,
            name="environment_type",
            values_callable=enum_values,
        ),
        nullable=False,
        default=EnvironmentType.DEVELOPMENT,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    base_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
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


class ProjectIntegration(Base):
    __tablename__ = "project_integrations"

    __table_args__ = (
        Index("ix_project_integrations_project_id", "project_id"),
        Index("ix_project_integrations_environment_id", "environment_id"),
        Index("ix_project_integrations_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    environment_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("project_environments.id", ondelete="SET NULL"),
        nullable=True,
    )

    integration_type: Mapped[IntegrationType] = mapped_column(
        SQLAlchemyEnum(
            IntegrationType,
            name="integration_type",
            values_callable=enum_values,
        ),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    external_reference: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    status: Mapped[IntegrationStatus] = mapped_column(
        SQLAlchemyEnum(
            IntegrationStatus,
            name="integration_status",
            values_callable=enum_values,
        ),
        nullable=False,
        default=IntegrationStatus.PENDING,
        server_default=IntegrationStatus.PENDING.value,
    )

    configuration: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    secret_reference: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    last_seen_at: Mapped[datetime | None] = mapped_column(
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


class ProjectEvent(Base):
    __tablename__ = "project_events"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "deduplication_key",
            name="uq_project_events_deduplication",
        ),
        Index("ix_project_events_project_occurred", "project_id", "occurred_at"),
        Index("ix_project_events_severity", "severity"),
        Index("ix_project_events_integration_id", "integration_id"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    environment_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("project_environments.id", ondelete="SET NULL"),
        nullable=True,
    )

    integration_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("project_integrations.id", ondelete="SET NULL"),
        nullable=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    severity: Mapped[EventSeverity] = mapped_column(
        SQLAlchemyEnum(
            EventSeverity,
            name="event_severity",
            values_callable=enum_values,
        ),
        nullable=False,
        default=EventSeverity.INFO,
        server_default=EventSeverity.INFO.value,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    payload: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    source_event_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    deduplication_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class ProjectIncident(Base):
    __tablename__ = "project_incidents"

    __table_args__ = (
        Index("ix_project_incidents_project_status", "project_id", "status"),
        Index("ix_project_incidents_severity", "severity"),
        CheckConstraint(
            "resolved_at IS NULL OR resolved_at >= detected_at",
            name="ck_project_incidents_resolution_time",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    environment_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("project_environments.id", ondelete="SET NULL"),
        nullable=True,
    )

    related_event_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("project_events.id", ondelete="SET NULL"),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    severity: Mapped[EventSeverity] = mapped_column(
        SQLAlchemyEnum(
            EventSeverity,
            name="incident_severity",
            values_callable=enum_values,
        ),
        nullable=False,
    )

    status: Mapped[IncidentStatus] = mapped_column(
        SQLAlchemyEnum(
            IncidentStatus,
            name="incident_status",
            values_callable=enum_values,
        ),
        nullable=False,
        default=IncidentStatus.OPEN,
        server_default=IncidentStatus.OPEN.value,
    )

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    acknowledged_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    resolved_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
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
