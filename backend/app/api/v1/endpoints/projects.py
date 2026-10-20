from app.api.v1.access import authorize_project, get_project
from app.api.v1.deps import Principal, get_principal, require_role
from app.core.database import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services import audit
from app.services.slug import slugify, unique_slug
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

router = APIRouter(tags=["projects"])


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(
    workspace_id: str = Query(...),
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[ProjectOut]:
    require_role(db, workspace_id, user, "viewer")
    projects = (
        db.query(Project)
        .filter(Project.workspace_id == workspace_id)
        .order_by(Project.created_at)
        .all()
    )
    return [ProjectOut.model_validate(project) for project in projects]


@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> ProjectOut:
    require_role(db, payload.workspace_id, user, "developer")
    project = Project(
        workspace_id=payload.workspace_id,
        name=payload.name,
        slug=unique_slug(slugify(payload.name)),
        repository_url=payload.repository_url,
    )
    db.add(project)
    audit.record(
        db,
        action="project.create",
        target_type="project",
        workspace_id=payload.workspace_id,
        user_id=user.id,
        target_id=project.id,
    )
    db.commit()
    db.refresh(project)
    return ProjectOut.model_validate(project)


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project_detail(
    project_id: str,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> ProjectOut:
    project = get_project(db, project_id)
    authorize_project(db, project, user)
    return ProjectOut.model_validate(project)


@router.patch("/projects/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> ProjectOut:
    project = get_project(db, project_id)
    workspace_id = authorize_project(db, project, user, "developer")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(project, field, value)
    audit.record(
        db,
        action="project.update",
        target_type="project",
        workspace_id=workspace_id,
        user_id=user.id,
        target_id=project.id,
        meta={"fields": list(updates)},
    )
    db.commit()
    db.refresh(project)
    return ProjectOut.model_validate(project)
