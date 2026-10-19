from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel

Severity = Literal["critical", "high", "medium", "low"]
IncidentStatus = Literal["open", "acknowledged", "resolved"]


class DeploymentCreate(BaseModel):
    commit_sha: str = Field(min_length=7, max_length=64)
    branch: str | None = Field(default=None, max_length=255)
    pull_request: int | None = None
    status: str = "pending"
    deployed_at: datetime | None = None
    meta: dict = Field(default_factory=dict)


class DeploymentOut(ORMModel):
    id: str
    environment_id: str
    commit_sha: str
    branch: str | None
    pull_request: int | None
    status: str
    deployed_at: datetime | None
    meta: dict
    created_at: datetime


class IncidentUpdate(BaseModel):
    status: IncidentStatus | None = None
    severity: Severity | None = None


class IncidentOut(ORMModel):
    id: str
    workspace_id: str
    project_id: str
    environment_id: str | None
    title: str
    severity: Severity
    status: IncidentStatus
    dedupe_key: str
    opened_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None


class IncidentEventOut(ORMModel):
    id: str
    incident_id: str
    type: str
    message: str
    meta: dict
    created_at: datetime
