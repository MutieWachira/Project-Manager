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
