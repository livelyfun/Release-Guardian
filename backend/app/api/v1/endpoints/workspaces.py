from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, get_membership, require_role
from app.core.database import get_db
from app.models.identity import AuditLog, Membership, User, Workspace
from app.schemas.identity import (
    AuditLogOut,
    MemberCreate,
    MemberOut,
    MemberUpdate,
    WorkspaceCreate,
    WorkspaceOut,
)
from app.services import audit
from app.services.slug import slugify, unique_slug

router = APIRouter(tags=["workspaces"])


def _member_out(member: Membership) -> MemberOut:
    return MemberOut(
        id=member.id,
        workspace_id=member.workspace_id,
        user_id=member.user_id,
        role=member.role,
        email=member.user.email if member.user is not None else None,
        name=member.user.name if member.user is not None else None,
        created_at=member.created_at,
    )


def _owner_count(db: Session, workspace_id: str, exclude_id: str | None = None) -> int:
    query = db.query(Membership).filter(
        Membership.workspace_id == workspace_id, Membership.role == "owner"
    )
    if exclude_id:
        query = query.filter(Membership.id != exclude_id)
    return query.count()


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
    return [_member_out(member) for member in members]


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
    return _member_out(membership)


@router.patch(
    "/workspaces/{workspace_id}/members/{membership_id}",
    response_model=MemberOut,
)
def update_member_role(
    workspace_id: str,
    membership_id: str,
    payload: MemberUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MemberOut:
    actor = require_role(db, workspace_id, user, "admin")
    target = (
        db.query(Membership)
        .filter(Membership.id == membership_id, Membership.workspace_id == workspace_id)
        .one_or_none()
    )
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if (target.role == "owner" or payload.role == "owner") and actor.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an owner can grant or change the owner role",
        )
    if (
        target.role == "owner"
        and payload.role != "owner"
        and _owner_count(db, workspace_id, exclude_id=target.id) == 0
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A workspace must keep at least one owner",
        )

    previous_role = target.role
    target.role = payload.role
    audit.record(
        db,
        action="member.role_update",
        target_type="user",
        workspace_id=workspace_id,
        user_id=user.id,
        target_id=target.user_id,
        meta={"from": previous_role, "to": payload.role},
    )
    db.commit()
    db.refresh(target)
    return _member_out(target)


@router.delete(
    "/workspaces/{workspace_id}/members/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_member(
    workspace_id: str,
    membership_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    actor = require_role(db, workspace_id, user, "admin")
    target = (
        db.query(Membership)
        .filter(Membership.id == membership_id, Membership.workspace_id == workspace_id)
        .one_or_none()
    )
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if target.role == "owner" and actor.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an owner can remove an owner",
        )
    if target.role == "owner" and _owner_count(db, workspace_id, exclude_id=target.id) == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A workspace must keep at least one owner",
        )

    audit.record(
        db,
        action="member.remove",
        target_type="user",
        workspace_id=workspace_id,
        user_id=user.id,
        target_id=target.user_id,
        meta={"role": target.role},
    )
    db.delete(target)
    db.commit()


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
