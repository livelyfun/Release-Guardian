from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel

Role = Literal["owner", "admin", "developer", "viewer"]


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class WorkspaceOut(ORMModel):
    id: str
    name: str
    slug: str
    role: Role
    created_at: datetime


class MemberCreate(BaseModel):
    email: str
    role: Role = "viewer"


class MemberOut(ORMModel):
    id: str
    workspace_id: str
    user_id: str
    role: Role
    created_at: datetime


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    scopes: list[str] = Field(default_factory=list)


class ApiKeyOut(ORMModel):
    id: str
    workspace_id: str
    name: str
    prefix: str
    scopes: list[str]
    revoked_at: datetime | None
    created_at: datetime
    key: str | None = None


class AuditLogOut(ORMModel):
    id: str
    workspace_id: str | None
    user_id: str | None
    action: str
    target_type: str
    target_id: str | None
    meta: dict
    created_at: datetime
