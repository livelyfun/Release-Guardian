from sqlalchemy.orm import Session

from app.models.identity import AuditLog


def record(
    db: Session,
    *,
    action: str,
    target_type: str,
    workspace_id: str | None = None,
    user_id: str | None = None,
    target_id: str | None = None,
    meta: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        workspace_id=workspace_id,
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        meta=meta or {},
    )
    db.add(entry)
    return entry
