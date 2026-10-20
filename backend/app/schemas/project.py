from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel, validate_http_url

MonitorKind = Literal["http", "browser", "lighthouse"]


class ProjectCreate(BaseModel):
    workspace_id: str
    name: str = Field(min_length=1, max_length=200)
    repository_url: str | None = None

    @field_validator("repository_url")
    @classmethod
    def _check_repo(cls, value: str | None) -> str | None:
        return validate_http_url(value) if value else value


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    repository_url: str | None = None
    archived: bool | None = None


class ProjectOut(ORMModel):
    id: str
    workspace_id: str
    name: str
    slug: str
    repository_url: str | None
    archived: bool
    created_at: datetime


class EnvironmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    base_url: str
    is_production: bool = False

    @field_validator("base_url")
    @classmethod
    def _check_base(cls, value: str) -> str:
        return validate_http_url(value)


class EnvironmentOut(ORMModel):
    id: str
    project_id: str
    name: str
    base_url: str
    is_production: bool
    created_at: datetime


class MonitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    kind: MonitorKind = "http"
    target_url: str
    interval_seconds: int = Field(default=300, ge=30, le=86400)
    config: dict = Field(default_factory=dict)

    @field_validator("target_url")
    @classmethod
    def _check_target(cls, value: str) -> str:
        return validate_http_url(value)


class MonitorUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    target_url: str | None = None
    interval_seconds: int | None = Field(default=None, ge=30, le=86400)
    enabled: bool | None = None
    config: dict | None = None
    kind: str | None = None


class MonitorOut(ORMModel):
    id: str
    environment_id: str
    name: str
    kind: MonitorKind
    target_url: str
    interval_seconds: int
    enabled: bool
    config: dict
    last_checked_at: datetime | None
    created_at: datetime


class RegressionSuppressionIn(BaseModel):
    until: datetime
    reason: str = Field(default="", max_length=300)


class RegressionSuppressionOut(BaseModel):
    monitor_id: str
    active: bool
    until: datetime | None
    reason: str
