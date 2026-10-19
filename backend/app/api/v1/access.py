from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import require_role
from app.models.execution import Run
from app.models.identity import User
from app.models.project import Environment, Monitor, Project


def get_project(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def get_environment(db: Session, environment_id: str) -> Environment:
    environment = db.get(Environment, environment_id)
    if environment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Environment not found")
    return environment


def get_monitor(db: Session, monitor_id: str) -> Monitor:
    monitor = db.get(Monitor, monitor_id)
    if monitor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found")
    return monitor


def get_run(db: Session, run_id: str) -> Run:
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


def authorize_project(db: Session, project: Project, user: User, minimum: str = "viewer") -> str:
    require_role(db, project.workspace_id, user, minimum)
    return project.workspace_id


def authorize_environment(
    db: Session, environment: Environment, user: User, minimum: str = "viewer"
) -> str:
    project = get_project(db, environment.project_id)
    return authorize_project(db, project, user, minimum)


def authorize_monitor(db: Session, monitor: Monitor, user: User, minimum: str = "viewer") -> str:
    environment = get_environment(db, monitor.environment_id)
    return authorize_environment(db, environment, user, minimum)


def authorize_run(db: Session, run: Run, user: User, minimum: str = "viewer") -> str:
    environment = get_environment(db, run.environment_id)
    return authorize_environment(db, environment, user, minimum)
