from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.access import authorize_environment, get_environment
from app.api.v1.deps import Principal, get_principal, require_role
from app.core.database import get_db
from app.models.project import Environment, Project
from app.models.release import Deployment
from app.schemas.release import (
    DeploymentComparisonOut,
    DeploymentCreate,
    DeploymentOut,
)
from app.services import audit
from app.services.runs import (
    build_deployment_comparison,
    enqueue_runs_for_environment,
    refresh_deployment_status,
)

router = APIRouter(tags=["deployments"])


@router.get("/deployments", response_model=list[DeploymentOut])
def list_deployments(
    workspace_id: str = Query(...),
    limit: int = Query(default=100, le=500),
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[DeploymentOut]:
    require_role(db, workspace_id, user, "viewer")
    deployments = (
        db.query(Deployment)
        .join(Environment, Environment.id == Deployment.environment_id)
        .join(Project, Project.id == Environment.project_id)
        .filter(Project.workspace_id == workspace_id)
        .order_by(Deployment.created_at.desc())
        .limit(limit)
        .all()
    )
    return [DeploymentOut.model_validate(deployment) for deployment in deployments]


@router.get("/environments/{environment_id}/deployments", response_model=list[DeploymentOut])
def list_environment_deployments(
    environment_id: str,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[DeploymentOut]:
    environment = get_environment(db, environment_id)
    authorize_environment(db, environment, user)
    deployments = (
        db.query(Deployment)
        .filter(Deployment.environment_id == environment_id)
        .order_by(Deployment.created_at.desc())
        .all()
    )
    return [DeploymentOut.model_validate(deployment) for deployment in deployments]


@router.post(
    "/environments/{environment_id}/deployments",
    response_model=DeploymentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_deployment(
    environment_id: str,
    payload: DeploymentCreate,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> DeploymentOut:
    environment = get_environment(db, environment_id)
    workspace_id = authorize_environment(db, environment, user, "developer")

    deployment = Deployment(environment_id=environment_id, **payload.model_dump())
    db.add(deployment)
    audit.record(
        db,
        action="deployment.create",
        target_type="deployment",
        workspace_id=workspace_id,
        user_id=user.id,
        target_id=deployment.id,
    )
    db.commit()
    db.refresh(deployment)

    enqueue_runs_for_environment(
        db, environment_id, trigger="deployment", deployment_id=deployment.id
    )
    refresh_deployment_status(db, deployment.id)
    db.commit()
    db.refresh(deployment)
    return DeploymentOut.model_validate(deployment)


@router.get("/deployments/{deployment_id}", response_model=DeploymentOut)
def get_deployment_detail(
    deployment_id: str,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> DeploymentOut:
    deployment = db.get(Deployment, deployment_id)
    if deployment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment not found")
    authorize_environment(db, get_environment(db, deployment.environment_id), user)
    return DeploymentOut.model_validate(deployment)


@router.get(
    "/deployments/{deployment_id}/comparison",
    response_model=DeploymentComparisonOut,
)
def get_deployment_comparison(
    deployment_id: str,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> DeploymentComparisonOut:
    deployment = db.get(Deployment, deployment_id)
    if deployment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment not found")
    authorize_environment(db, get_environment(db, deployment.environment_id), user)
    return DeploymentComparisonOut.model_validate(
        build_deployment_comparison(db, deployment)
    )
