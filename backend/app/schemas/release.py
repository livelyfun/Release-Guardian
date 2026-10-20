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
    subject: str | None
    body: str | None
    next_attempt_at: datetime | None
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


class EscalationRuleCreate(_ChannelConfig):
    name: str = Field(min_length=1, max_length=120)
    severity: Severity = "high"
    minutes_to_escalate: int = Field(default=30, ge=0, le=10080)
    enabled: bool = True


class EscalationRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    severity: Severity | None = None
    minutes_to_escalate: int | None = Field(default=None, ge=0, le=10080)
    kind: ChannelKind | None = None
    config: dict | None = None
    enabled: bool | None = None


class EscalationRuleOut(ORMModel):
    id: str
    workspace_id: str
    name: str
    severity: Severity
    minutes_to_escalate: int
    channel_kind: str
    channel_config: dict
    is_enabled: bool
    created_at: datetime


class UsageRecordOut(ORMModel):
    id: str
    workspace_id: str
    metric: str
    quantity: float
    recorded_at: datetime


class MaintenanceWindowCreate(BaseModel):
    project_id: str | None = None
    environment_id: str | None = None
    monitor_id: str | None = None
    reason: str = Field(default="", max_length=300)
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def _validate_window(self):
        if (self.starts_at.tzinfo is None) != (self.ends_at.tzinfo is None):
            raise ValueError("starts_at and ends_at must both include a timezone or both omit it")
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        scopes = [self.project_id, self.environment_id, self.monitor_id]
        if sum(scope is not None for scope in scopes) > 1:
            raise ValueError("Choose at most one scope: project_id, environment_id, or monitor_id")
        return self


class MaintenanceWindowOut(ORMModel):
    id: str
    workspace_id: str
    project_id: str | None
    environment_id: str | None
    monitor_id: str | None
    reason: str
    starts_at: datetime
    ends_at: datetime
    created_at: datetime
