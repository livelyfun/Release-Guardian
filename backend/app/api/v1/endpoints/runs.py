from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.v1.access import authorize_monitor, authorize_run, get_monitor, get_run
from app.api.v1.deps import Principal, get_principal, require_role
from app.core.database import get_db
from app.models.execution import Run
from app.models.project import Environment, Project
from app.schemas.execution import RunCreate, RunDetailOut, RunOut
from app.services import audit
from app.workers.dispatch import dispatch_run

router = APIRouter(tags=["runs"])


@router.post(
    "/monitors/{monitor_id}/runs",
    response_model=RunOut,
    status_code=status.HTTP_201_CREATED,
)
def trigger_run(
    monitor_id: str,
    payload: RunCreate,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> RunOut:
    monitor = get_monitor(db, monitor_id)
    workspace_id = authorize_monitor(db, monitor, user, "developer")

    run = Run(
        monitor_id=monitor.id,
        environment_id=monitor.environment_id,
        status="pending",
        trigger=payload.trigger,
    )
    db.add(run)
    audit.record(
        db,
        action="run.trigger",
        target_type="run",
        workspace_id=workspace_id,
        user_id=user.id,
        target_id=run.id,
        meta={"monitor_id": monitor.id},
    )
    db.commit()
    db.refresh(run)

    dispatch_run(run.id)
    db.refresh(run)
    return RunOut.model_validate(run)


@router.get("/monitors/{monitor_id}/runs", response_model=list[RunOut])
def list_monitor_runs(
    monitor_id: str,
    limit: int = Query(default=50, le=200),
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[RunOut]:
    monitor = get_monitor(db, monitor_id)
    authorize_monitor(db, monitor, user)
    runs = (
        db.query(Run)
        .filter(Run.monitor_id == monitor_id)
        .order_by(Run.created_at.desc())
        .limit(limit)
        .all()
    )
    return [RunOut.model_validate(run) for run in runs]


@router.get("/runs", response_model=list[RunOut])
def list_runs(
    workspace_id: str = Query(...),
    limit: int = Query(default=100, le=500),
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[RunOut]:
    require_role(db, workspace_id, user, "viewer")
    runs = (
        db.query(Run)
        .join(Environment, Environment.id == Run.environment_id)
        .join(Project, Project.id == Environment.project_id)
        .filter(Project.workspace_id == workspace_id)
        .order_by(Run.created_at.desc())
        .limit(limit)
        .all()
    )
    return [RunOut.model_validate(run) for run in runs]


@router.get("/runs/{run_id}", response_model=RunDetailOut)
def get_run_detail(
    run_id: str,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> RunDetailOut:
    run = get_run(db, run_id)
    authorize_run(db, run, user)
    return RunDetailOut.model_validate(run)
