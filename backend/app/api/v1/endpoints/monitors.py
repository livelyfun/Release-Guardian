from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.v1.access import (
    authorize_environment,
    authorize_monitor,
    get_environment,
    get_monitor,
)
from app.api.v1.deps import Principal, get_principal, require_role
from app.core.database import get_db
from app.models.project import Environment, Monitor, Project
from app.schemas.project import MonitorCreate, MonitorOut, MonitorUpdate
from app.services import audit

router = APIRouter(tags=["monitors"])


def _list(db: Session, workspace_id: str | None, environment_id: str | None) -> list[MonitorOut]:
    query = db.query(Monitor)
    if environment_id:
        query = query.filter(Monitor.environment_id == environment_id)
    elif workspace_id:
        query = (
            query.join(Environment, Environment.id == Monitor.environment_id)
            .join(Project, Project.id == Environment.project_id)
            .filter(Project.workspace_id == workspace_id)
        )
    monitors = query.order_by(Monitor.created_at).all()
    return [MonitorOut.model_validate(monitor) for monitor in monitors]


@router.get("/monitors", response_model=list[MonitorOut])
def list_monitors(
    workspace_id: str | None = Query(default=None),
    environment_id: str | None = Query(default=None),
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[MonitorOut]:
    if environment_id:
        environment = get_environment(db, environment_id)
        authorize_environment(db, environment, user)
    elif workspace_id:
        require_role(db, workspace_id, user, "viewer")
    return _list(db, workspace_id, environment_id)


@router.get("/environments/{environment_id}/monitors", response_model=list[MonitorOut])
def list_environment_monitors(
    environment_id: str,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[MonitorOut]:
    environment = get_environment(db, environment_id)
    authorize_environment(db, environment, user)
    return _list(db, None, environment_id)


@router.post(
    "/environments/{environment_id}/monitors",
    response_model=MonitorOut,
    status_code=status.HTTP_201_CREATED,
)
def create_monitor(
    environment_id: str,
    payload: MonitorCreate,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> MonitorOut:
    environment = get_environment(db, environment_id)
    workspace_id = authorize_environment(db, environment, user, "developer")

    monitor = Monitor(environment_id=environment_id, **payload.model_dump())
    db.add(monitor)
    audit.record(
        db,
        action="monitor.create",
        target_type="monitor",
        workspace_id=workspace_id,
        user_id=user.id,
        target_id=monitor.id,
    )
    db.commit()
    db.refresh(monitor)
    return MonitorOut.model_validate(monitor)


@router.get("/monitors/{monitor_id}", response_model=MonitorOut)
def get_monitor_detail(
    monitor_id: str,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> MonitorOut:
    monitor = get_monitor(db, monitor_id)
    authorize_monitor(db, monitor, user)
    return MonitorOut.model_validate(monitor)


@router.patch("/monitors/{monitor_id}", response_model=MonitorOut)
def update_monitor(
    monitor_id: str,
    payload: MonitorUpdate,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> MonitorOut:
    monitor = get_monitor(db, monitor_id)
    workspace_id = authorize_monitor(db, monitor, user, "developer")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(monitor, field, value)
    audit.record(
        db,
        action="monitor.update",
        target_type="monitor",
        workspace_id=workspace_id,
        user_id=user.id,
        target_id=monitor.id,
        meta={"fields": list(updates)},
    )
    db.commit()
    db.refresh(monitor)
    return MonitorOut.model_validate(monitor)
