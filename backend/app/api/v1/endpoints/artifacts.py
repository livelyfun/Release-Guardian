from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.deps import Principal, get_principal, require_role
from app.core.config import settings
from app.core.database import get_db
from app.models.execution import Artifact, Run
from app.models.project import Environment, Project
from app.services.storage import StorageError, get_signed_url

router = APIRouter(tags=["artifacts"])


def _authorize_workspace(
    db: Session, workspace_id: str, user: Principal, minimum: str = "viewer"
) -> None:
    require_role(db, workspace_id, user, minimum)


def _authorize_artifact(
    db: Session, workspace_id: str, artifact_key: str
) -> Artifact:
    """Resolve an artifact key and prove it belongs to the workspace.

    A signed URL is a bearer credential, so the key itself must not be enough
    to obtain one.  Walk artifact → run → environment → project and return 404
    for anything outside the workspace, matching the rest of the API's
    non-disclosure behavior.
    """
    artifact = (
        db.query(Artifact).filter(Artifact.storage_key == artifact_key).one_or_none()
    )
    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found"
        )

    authorized = (
        db.query(Artifact.id)
        .join(Run, Run.id == Artifact.run_id)
        .join(Environment, Environment.id == Run.environment_id)
        .join(Project, Project.id == Environment.project_id)
        .filter(
            Artifact.id == artifact.id,
            Project.workspace_id == workspace_id,
        )
        .one_or_none()
    )
    if authorized is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found"
        )
    return artifact


@router.get(
    "/workspaces/{workspace_id}/artifacts/signed-url",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
def get_artifact_signed_url(
    workspace_id: str,
    artifact_key: str = Query(min_length=1, max_length=1000),
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Get a short-lived signed URL for an artifact in this workspace.

    The ``artifact_key`` is the ``storage_key`` value returned when the
    artifact was uploaded (e.g. ``artifacts/<run_id>/screenshot-<hash>``).
    """
    _authorize_workspace(db, workspace_id, user, "viewer")
    artifact = _authorize_artifact(db, workspace_id, artifact_key)
    try:
        url = get_signed_url(artifact.storage_key)
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return {
        "signed_url": url,
        "artifact_key": artifact.storage_key,
        "expires_in_seconds": settings.artifact_url_ttl_seconds,
    }
