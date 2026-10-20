"""Run admission control.

All run-creating paths (manual trigger, deployment, scheduler) share the same
backpressure rules so a burst of requests cannot exhaust worker or database
capacity.  The scheduler applies its own skip logic; this module covers the
API and deployment paths.
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.execution import Run
from app.models.project import Environment, Monitor, Project


class CapacityError(RuntimeError):
    """Base class for admission-control rejections."""


class MonitorBusyError(CapacityError):
    """The monitor already has a pending or running run."""


class WorkspaceCapacityError(CapacityError):
    """The workspace has reached its active-run ceiling."""


def active_run_for_monitor(db: Session, monitor_id: str) -> Run | None:
    return (
        db.query(Run)
        .filter(Run.monitor_id == monitor_id, Run.status.in_(["pending", "running"]))
        .first()
    )


def active_run_count_for_workspace(db: Session, workspace_id: str) -> int:
    return (
        db.query(func.count(Run.id))
        .join(Environment, Environment.id == Run.environment_id)
        .join(Project, Project.id == Environment.project_id)
        .filter(
            Project.workspace_id == workspace_id,
            Run.status.in_(["pending", "running"]),
        )
        .scalar()
        or 0
    )


def ensure_capacity(db: Session, monitor: Monitor, workspace_id: str) -> None:
    """Raise when a new run for ``monitor`` would exceed a configured ceiling."""
    if settings.max_active_runs_per_monitor > 0:
        active = active_run_for_monitor(db, monitor.id)
        if active is not None:
            raise MonitorBusyError(
                f"Monitor {monitor.id} already has an active run ({active.id})"
            )

    if settings.max_active_runs_per_workspace > 0:
        count = active_run_count_for_workspace(db, workspace_id)
        if count >= settings.max_active_runs_per_workspace:
            raise WorkspaceCapacityError(
                f"Workspace {workspace_id} has reached its active-run limit "
                f"({settings.max_active_runs_per_workspace})"
            )
