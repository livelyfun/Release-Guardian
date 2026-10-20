from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import Principal, get_principal, require_role
from app.core.database import get_db
from app.models.base import utcnow
from app.models.identity import ApiKey
from app.schemas.identity import ApiKeyCreate, ApiKeyOut
from app.services import audit
from app.services.slug import api_key as generate_api_key

router = APIRouter(tags=["api-keys"])


@router.get("/workspaces/{workspace_id}/api-keys", response_model=list[ApiKeyOut])
def list_api_keys(
    workspace_id: str,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[ApiKeyOut]:
    require_role(db, workspace_id, user, "viewer")
    keys = (
        db.query(ApiKey)
        .filter(ApiKey.workspace_id == workspace_id)
        .order_by(ApiKey.created_at.desc())
        .all()
    )
    return [ApiKeyOut.model_validate(key) for key in keys]


@router.post(
    "/workspaces/{workspace_id}/api-keys",
    response_model=ApiKeyOut,
    status_code=status.HTTP_201_CREATED,
)
def create_api_key(
    workspace_id: str,
    payload: ApiKeyCreate,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> ApiKeyOut:
    require_role(db, workspace_id, user, "admin")
    raw, prefix, digest = generate_api_key()
    key = ApiKey(
        workspace_id=workspace_id,
        created_by=user.id,
        name=payload.name,
        prefix=prefix,
        key_hash=digest,
        scopes=payload.scopes,
    )
    db.add(key)
    audit.record(
        db,
        action="api_key.create",
        target_type="api_key",
        workspace_id=workspace_id,
        user_id=user.id,
        target_id=key.id,
    )
    db.commit()
    db.refresh(key)
    out = ApiKeyOut.model_validate(key)
    out.key = raw
    return out


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: str,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> None:
    key = db.get(ApiKey, key_id)
    if key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    require_role(db, key.workspace_id, user, "admin")
    if key.revoked_at is None:
        key.revoked_at = utcnow()
        audit.record(
            db,
            action="api_key.revoke",
            target_type="api_key",
            workspace_id=key.workspace_id,
            user_id=user.id,
            target_id=key.id,
        )
    db.commit()
