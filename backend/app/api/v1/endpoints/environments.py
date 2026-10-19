from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.v1.access import authorize_environment, authorize_project, get_environment, get_project
from app.api.v1.deps import get_current_user, require_role
from app.core.database import get_db
from app.models.identity import User
from app.models.project import Environment, Project
from app.schemas.project import EnvironmentCreate, EnvironmentOut
from app.services import audit

router = APIRouter(tags=["environments"])


@router.get("/environments", response_model=list[EnvironmentOut])
def list_environments(
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EnvironmentOut]:
    require_role(db, workspace_id, user, "viewer")
    environments = (
        db.query(Environment)
        .join(Project, Project.id == Environment.project_id)
        .filter(Project.workspace_id == workspace_id)
        .order_by(Environment.created_at)
        .all()
    )
    return [EnvironmentOut.model_validate(environment) for environment in environments]


@router.get("/projects/{project_id}/environments", response_model=list[EnvironmentOut])
def list_project_environments(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EnvironmentOut]:
    project = get_project(db, project_id)
    authorize_project(db, project, user)
    environments = (
        db.query(Environment)
        .filter(Environment.project_id == project_id)
        .order_by(Environment.created_at)
        .all()
    )
    return [EnvironmentOut.model_validate(environment) for environment in environments]


@router.post(
    "/projects/{project_id}/environments",
    response_model=EnvironmentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_environment(
    project_id: str,
    payload: EnvironmentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EnvironmentOut:
    project = get_project(db, project_id)
    workspace_id = authorize_project(db, project, user, "developer")

    environment = Environment(project_id=project_id, **payload.model_dump())
    db.add(environment)
    audit.record(
        db,
        action="environment.create",
        target_type="environment",
        workspace_id=workspace_id,
        user_id=user.id,
        target_id=environment.id,
    )
    db.commit()
    db.refresh(environment)
    return EnvironmentOut.model_validate(environment)


@router.get("/environments/{environment_id}", response_model=EnvironmentOut)
def get_environment_detail(
    environment_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EnvironmentOut:
    environment = get_environment(db, environment_id)
    authorize_environment(db, environment, user)
    return EnvironmentOut.model_validate(environment)
