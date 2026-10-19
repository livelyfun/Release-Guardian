from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, require_role
from app.core.database import get_db
from app.models.identity import User
from app.models.release import NotificationAttempt, NotificationChannel
from app.schemas.release import (
    NotificationAttemptOut,
    NotificationChannelCreate,
    NotificationChannelOut,
    NotificationChannelUpdate,
)
from app.services import audit

router = APIRouter(tags=["notifications"])


def _authorize_channel(db: Session, channel_id: str, user: User, role: str) -> NotificationChannel:
    channel = db.get(NotificationChannel, channel_id)
    if channel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification channel not found"
        )
    require_role(db, channel.workspace_id, user, role)
    return channel


@router.get(
    "/workspaces/{workspace_id}/notification-channels",
    response_model=list[NotificationChannelOut],
)
def list_channels(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NotificationChannelOut]:
    require_role(db, workspace_id, user, "viewer")
    channels = (
        db.query(NotificationChannel)
        .filter(NotificationChannel.workspace_id == workspace_id)
        .order_by(NotificationChannel.created_at.desc())
        .all()
    )
    return [NotificationChannelOut.model_validate(channel) for channel in channels]


@router.post(
    "/workspaces/{workspace_id}/notification-channels",
    response_model=NotificationChannelOut,
    status_code=status.HTTP_201_CREATED,
)
def create_channel(
    workspace_id: str,
    payload: NotificationChannelCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationChannelOut:
    require_role(db, workspace_id, user, "admin")
    channel = NotificationChannel(
        workspace_id=workspace_id,
        kind=payload.kind,
        config=payload.config,
        enabled=payload.enabled,
    )
    db.add(channel)
    audit.record(
        db,
        action="notification_channel.create",
        target_type="notification_channel",
        workspace_id=workspace_id,
        user_id=user.id,
        target_id=channel.id,
        meta={"kind": channel.kind},
    )
    db.commit()
    db.refresh(channel)
    return NotificationChannelOut.model_validate(channel)


@router.patch(
    "/notification-channels/{channel_id}", response_model=NotificationChannelOut
)
def update_channel(
    channel_id: str,
    payload: NotificationChannelUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationChannelOut:
    channel = _authorize_channel(db, channel_id, user, "admin")
    kind = payload.kind or channel.kind
    config = payload.config if payload.config is not None else channel.config
    NotificationChannelCreate(kind=kind, config=config)

    channel.kind = kind
    channel.config = config
    if payload.enabled is not None:
        channel.enabled = payload.enabled

    audit.record(
        db,
        action="notification_channel.update",
        target_type="notification_channel",
        workspace_id=channel.workspace_id,
        user_id=user.id,
        target_id=channel.id,
        meta=payload.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(channel)
    return NotificationChannelOut.model_validate(channel)


@router.delete("/notification-channels/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_channel(
    channel_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    channel = _authorize_channel(db, channel_id, user, "admin")
    audit.record(
        db,
        action="notification_channel.delete",
        target_type="notification_channel",
        workspace_id=channel.workspace_id,
        user_id=user.id,
        target_id=channel.id,
    )
    db.delete(channel)
    db.commit()


@router.get(
    "/notification-channels/{channel_id}/attempts",
    response_model=list[NotificationAttemptOut],
)
def list_attempts(
    channel_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NotificationAttemptOut]:
    channel = _authorize_channel(db, channel_id, user, "viewer")
    attempts = (
        db.query(NotificationAttempt)
        .filter(NotificationAttempt.channel_id == channel.id)
        .order_by(NotificationAttempt.created_at.desc())
        .limit(100)
        .all()
    )
    return [NotificationAttemptOut.model_validate(attempt) for attempt in attempts]
