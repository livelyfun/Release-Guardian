from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel, validate_http_url

Severity = Literal["critical", "high", "medium", "low"]
IncidentStatus = Literal["open", "acknowledged", "resolved"]
ChannelKind = Literal["webhook", "email"]


class _ChannelConfig(BaseModel):
    kind: ChannelKind = "webhook"
    config: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_config(self):
        if self.kind == "webhook":
            url = self.config.get("url")
            if not isinstance(url, str) or not url:
                raise ValueError("Webhook channels require config.url")
            validate_http_url(url)
        elif self.kind == "email":
            to = self.config.get("to")
            if not isinstance(to, str) or not to:
                raise ValueError("Email channels require config.to")
        return self


class NotificationChannelCreate(_ChannelConfig):
    enabled: bool = True


class NotificationChannelUpdate(BaseModel):
    kind: ChannelKind | None = None
    config: dict | None = None
    enabled: bool | None = None


class NotificationChannelOut(ORMModel):
    id: str
    workspace_id: str
    kind: ChannelKind
    config: dict
    enabled: bool
    created_at: datetime


class NotificationAttemptOut(ORMModel):
    id: str
    channel_id: str
    incident_id: str | None
    status: str
    attempt: int
    error: str | None
    created_at: datetime


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


class UsageRecordOut(ORMModel):
    id: str
    workspace_id: str
    metric: str
    quantity: float
    recorded_at: datetime
