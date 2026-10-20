from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, get_membership, require_role
from app.core.database import get_db
from app.models.identity import AuditLog, Membership, User, Workspace
from app.schemas.identity import (
    AuditLogOut,
    MemberCreate,
    MemberOut,
    WorkspaceCreate,
    WorkspaceOut,
)
from app.services import audit
from app.services.slug import slugify, unique_slug

router = APIRouter(tags=["workspaces"])


@router.get("/workspaces", response_model=list[WorkspaceOut])
def list_workspaces(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[WorkspaceOut]:
    rows = (
        db.query(Workspace, Membership.role)
        .join(Membership, Membership.workspace_id == Workspace.id)
        .filter(Membership.user_id == user.id)
        .order_by(Workspace.created_at)
        .all()
    )
    return [
        WorkspaceOut(id=ws.id, name=ws.name, slug=ws.slug, role=role, created_at=ws.created_at)
        for ws, role in rows
    ]


@router.post("/workspaces", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceOut:
    workspace = Workspace(name=payload.name, slug=unique_slug(slugify(payload.name)), owner_id=user.id)
    db.add(workspace)
    db.flush()
    db.add(Membership(workspace_id=workspace.id, user_id=user.id, role="owner"))
    audit.record(
        db,
        action="workspace.create",
        target_type="workspace",
        workspace_id=workspace.id,
        user_id=user.id,
        target_id=workspace.id,
    )
    db.commit()
    db.refresh(workspace)
    return WorkspaceOut(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        role="owner",
        created_at=workspace.created_at,
    )


@router.get("/workspaces/{workspace_id}/members", response_model=list[MemberOut])
def list_members(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MemberOut]:
    get_membership(db, workspace_id, user)
    members = (
        db.query(Membership)
        .filter(Membership.workspace_id == workspace_id)
        .order_by(Membership.created_at)
        .all()
    )
    return [MemberOut.model_validate(member) for member in members]


@router.post(
    "/workspaces/{workspace_id}/members",
    response_model=MemberOut,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    workspace_id: str,
    payload: MemberCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MemberOut:
    require_role(db, workspace_id, user, "admin")
    invitee = db.query(User).filter(User.email == payload.email.lower()).one_or_none()
    if invitee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    existing = (
        db.query(Membership)
        .filter(Membership.workspace_id == workspace_id, Membership.user_id == invitee.id)
        .one_or_none()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already a member")

    membership = Membership(workspace_id=workspace_id, user_id=invitee.id, role=payload.role)
    db.add(membership)
    audit.record(
        db,
        action="member.add",
        target_type="user",
        workspace_id=workspace_id,
        user_id=user.id,
        target_id=invitee.id,
        meta={"role": payload.role},
    )
    db.commit()
    db.refresh(membership)
    return MemberOut.model_validate(membership)


@router.get("/workspaces/{workspace_id}/audit-logs", response_model=list[AuditLogOut])
def list_audit_logs(
    workspace_id: str,
    limit: int = 100,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AuditLogOut]:
    get_membership(db, workspace_id, user)
    entries = (
        db.query(AuditLog)
        .filter(AuditLog.workspace_id == workspace_id)
        .order_by(AuditLog.created_at.desc())
        .limit(min(limit, 500))
        .all()
    )
    return [AuditLogOut.model_validate(entry) for entry in entries]
