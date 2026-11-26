from enum import Enum


class ProjectStatus(str, Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ProjectRole(str, Enum):
    OWNER = "owner"
    MANAGER = "manager"
    CONTRIBUTOR = "contribution"
    VIEWER = "viewer"


class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    CUSTOM = "custom"


class IntegrationType(str, Enum):
    GITHUB = "github"
    SERVER_AGENT = "server_agent"
    APPLICATION = "application"
    DATABASE = "database"


class IntegrationStatus(str, Enum):
    PENDING = "pending"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class EventSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class IncidentStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
