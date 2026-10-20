"""Maintenance-window alert suppression.

Checks still execute during a window so the dashboard keeps a continuous
history; only incident creation is suppressed. A successful run during the
window still resolves incidents opened before it started.
"""

from datetime import UTC, datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.project import Monitor, Project
from app.models.release import MaintenanceWindow


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def active_maintenance_window(
    db: Session, project: Project, monitor: Monitor, now: datetime | None = None
) -> MaintenanceWindow | None:
    """Return the most specific active window for this monitor, if any."""
    current = now or datetime.now(UTC)
    return (
        db.query(MaintenanceWindow)
        .filter(
            MaintenanceWindow.workspace_id == project.workspace_id,
            MaintenanceWindow.starts_at <= current,
            MaintenanceWindow.ends_at > current,
            or_(
                MaintenanceWindow.monitor_id == monitor.id,
                MaintenanceWindow.environment_id == monitor.environment_id,
                MaintenanceWindow.project_id == project.id,
                and_(
                    MaintenanceWindow.monitor_id.is_(None),
                    MaintenanceWindow.environment_id.is_(None),
                    MaintenanceWindow.project_id.is_(None),
                ),
            ),
        )
        .order_by(
            MaintenanceWindow.monitor_id.is_(None).asc(),
            MaintenanceWindow.environment_id.is_(None).asc(),
            MaintenanceWindow.project_id.is_(None).asc(),
            MaintenanceWindow.created_at.desc(),
        )
        .first()
    )


def window_summary(window: MaintenanceWindow) -> dict:
    return {
        "id": window.id,
        "reason": window.reason,
        "starts_at": _as_utc(window.starts_at).isoformat(),
        "ends_at": _as_utc(window.ends_at).isoformat(),
    }
