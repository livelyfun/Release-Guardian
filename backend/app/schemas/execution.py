from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.common import ORMModel

RunStatus = Literal["pending", "running", "passed", "failed", "inconclusive"]


class RunCreate(BaseModel):
    trigger: Literal["manual", "scheduled", "deployment"] = "manual"


class StepResultOut(ORMModel):
    id: str
    step_index: int
    name: str
    status: RunStatus
    duration_ms: int | None
    error: str | None
    evidence: dict


class RunOut(ORMModel):
    id: str
    monitor_id: str
    environment_id: str
    deployment_id: str | None
    status: RunStatus
    trigger: str
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    summary: dict
    created_at: datetime


class RunDetailOut(RunOut):
    steps: list[StepResultOut]


class ArtifactOut(ORMModel):
    id: str
    run_id: str
    kind: str
    storage_key: str
    url: str | None
    size_bytes: int | None
    mime_type: str | None
    created_at: datetime
