from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import Principal, get_principal, require_role
from app.core.database import get_db
from app.models.project import Project
from app.services.storage import get_signed_url, StorageError

router = APIRouter(tags=["artifacts"])


def _authorize_workspace(
    db: Session, workspace_id: str, user: Principal, minimum: str = "viewer"
) -> None:
    require_role(db, workspace_id, user, minimum)


@router.get(
    "/workspaces/{workspace_id}/artifacts/{artifact_key}/signed-url",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
def get_artifact_signed_url(
    workspace_id: str,
    artifact_key: str,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Get a short-lived signed URL for an artifact.

    The ``artifact_key`` is the ``storage_key`` value returned when the
    artifact was uploaded (e.g. ``artifacts/<run_id>/screenshot-<hash>``).
    The URL is valid for 7 days and is scoped to the workspace.
    """
    _authorize_workspace(db, workspace_id, user, "viewer")
    try:
        url = get_signed_url(artifact_key)
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return {"signed_url": url, "artifact_key": artifact_key, "expires_in_seconds": 604800}