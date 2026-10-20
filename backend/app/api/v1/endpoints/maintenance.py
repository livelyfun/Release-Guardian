from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import Principal, get_principal, require_role
from app.core.database import get_db
from app.models.project import Environment, Monitor, Project
from app.models.release import MaintenanceWindow
from app.schemas.release import MaintenanceWindowCreate, MaintenanceWindowOut
from app.services import audit

router = APIRouter(tags=["maintenance"])


def _authorize_window(
    db: Session, window_id: str, user: Principal, role: str
) -> MaintenanceWindow:
    window = db.get(MaintenanceWindow, window_id)
    if window is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance window not found"
        )
    require_role(db, window.workspace_id, user, role)
    return window


def _validate_scope(db: Session, workspace_id: str, payload: MaintenanceWindowCreate) -> None:
    """Reject scopes that do not belong to the workspace (404, not 403)."""
    if payload.project_id is not None:
        project = db.get(Project, payload.project_id)
        if project is None or project.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )
    if payload.environment_id is not None:
        environment = db.get(Environment, payload.environment_id)
        project = db.get(Project, environment.project_id) if environment else None
        if environment is None or project is None or project.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Environment not found"
            )
    if payload.monitor_id is not None:
        monitor = db.get(Monitor, payload.monitor_id)
        environment = db.get(Environment, monitor.environment_id) if monitor else None
        project = db.get(Project, environment.project_id) if environment else None
        if monitor is None or project is None or project.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found"
            )


@router.get(
    "/workspaces/{workspace_id}/maintenance-windows",
    response_model=list[MaintenanceWindowOut],
)
def list_maintenance_windows(
    workspace_id: str,
    active_only: bool = False,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[MaintenanceWindowOut]:
    require_role(db, workspace_id, user, "viewer")
    query = db.query(MaintenanceWindow).filter(
        MaintenanceWindow.workspace_id == workspace_id
    )
    if active_only:
        now = datetime.now(UTC)
        query = query.filter(
            MaintenanceWindow.starts_at <= now,
            MaintenanceWindow.ends_at > now,
        )
    windows = query.order_by(MaintenanceWindow.starts_at.desc()).all()
    return [MaintenanceWindowOut.model_validate(window) for window in windows]


@router.post(
    "/workspaces/{workspace_id}/maintenance-windows",
    response_model=MaintenanceWindowOut,
    status_code=status.HTTP_201_CREATED,
)
def create_maintenance_window(
    workspace_id: str,
    payload: MaintenanceWindowCreate,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> MaintenanceWindowOut:
    require_role(db, workspace_id, user, "admin")
    _validate_scope(db, workspace_id, payload)

    window = MaintenanceWindow(
        workspace_id=workspace_id,
        project_id=payload.project_id,
        environment_id=payload.environment_id,
        monitor_id=payload.monitor_id,
        reason=payload.reason,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
    )
    db.add(window)
    audit.record(
        db,
        action="maintenance_window.create",
        target_type="maintenance_window",
        workspace_id=workspace_id,
        user_id=user.id,
        target_id=window.id,
        meta={
            "project_id": payload.project_id,
            "environment_id": payload.environment_id,
            "monitor_id": payload.monitor_id,
            "starts_at": payload.starts_at.isoformat(),
            "ends_at": payload.ends_at.isoformat(),
        },
    )
    db.commit()
    db.refresh(window)
    return MaintenanceWindowOut.model_validate(window)


@router.delete(
    "/maintenance-windows/{window_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_maintenance_window(
    window_id: str,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> None:
    window = _authorize_window(db, window_id, user, "admin")
    audit.record(
        db,
        action="maintenance_window.delete",
        target_type="maintenance_window",
        workspace_id=window.workspace_id,
        user_id=user.id,
        target_id=window.id,
    )
    db.delete(window)
    db.commit()
