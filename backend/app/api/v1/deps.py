from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.identity import ApiKey, Membership, User
from app.services.slug import hash_api_key

ROLE_RANK = {"viewer": 0, "developer": 1, "admin": 2, "owner": 3}
KEY_SCOPE_RANK = {"read": 0, "viewer": 0, "write": 1, "developer": 1, "admin": 2, "*": 2}


@dataclass
class Principal:
    user: User | None = None
    api_key: ApiKey | None = None

    @property
    def id(self) -> str | None:
        return self.user.id if self.user is not None else None

    @property
    def workspace_id(self) -> str | None:
        return self.api_key.workspace_id if self.api_key is not None else None

    @property
    def role(self) -> str | None:
        if self.api_key is None:
            return None
        return _scope_role(self.api_key.scopes)


def _scope_role(scopes: list[str]) -> str:
    highest = max((KEY_SCOPE_RANK.get(scope, -1) for scope in scopes), default=0)
    for role, rank in ROLE_RANK.items():
        if rank == highest:
            return role
    return "viewer"


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return authorization.split(" ", 1)[1].strip()


def _user_from_token(token: str, db: Session) -> User:
    try:
        payload = decode_token(token)
    except Exception as exc:  # noqa: BLE001 - normalize all JWT errors
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        ) from exc

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user = db.get(User, payload.get("sub"))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    user = _user_from_token(_bearer(authorization), db)
    return user


def get_principal(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Principal:
    token = _bearer(authorization)
    if token.startswith("rg_"):
        key = (
            db.query(ApiKey)
            .filter(ApiKey.key_hash == hash_api_key(token), ApiKey.revoked_at.is_(None))
            .one_or_none()
        )
        if key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked API key"
            )
        return Principal(api_key=key)
    return Principal(user=_user_from_token(token, db))


def get_membership(db: Session, workspace_id: str, user: User | Principal) -> Membership | None:
    if isinstance(user, Principal):
        if user.api_key is not None:
            if user.api_key.workspace_id != workspace_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
                )
            return None
        user = user.user
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    membership = (
        db.query(Membership)
        .filter(Membership.workspace_id == workspace_id, Membership.user_id == user.id)
        .one_or_none()
    )
    if membership is None:
        # Do not reveal whether the workspace exists to non-members.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return membership


def require_role(
    db: Session, workspace_id: str, user: User | Principal, minimum: str
) -> Membership | None:
    if isinstance(user, Principal) and user.api_key is not None:
        if user.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
            )
        if ROLE_RANK.get(user.role or "viewer", -1) < ROLE_RANK[minimum]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key requires {minimum} scope or higher",
            )
        return None

    membership = get_membership(db, workspace_id, user)
    assert membership is not None
    if ROLE_RANK.get(membership.role, -1) < ROLE_RANK[minimum]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires {minimum} role or higher",
        )
    return membership
