from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.deps import Principal, get_principal, require_role
from app.core.database import get_db
from app.models.release import UsageRecord
from app.schemas.release import UsageRecordOut, UsageSummaryOut

router = APIRouter(tags=["usage"])


def _authorize_workspace(
    db: Session, workspace_id: str, user: Principal, minimum: str = "viewer"
) -> None:
    require_role(db, workspace_id, user, minimum)


@router.get(
    "/workspaces/{workspace_id}/usage",
    response_model=list[UsageRecordOut],
    status_code=status.HTTP_200_OK,
)
def list_usage(
    workspace_id: str,
    metric: str | None = Query(default=None, description="Filter by metric name"),
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[UsageRecordOut]:
    """List usage records for a workspace."""
    _authorize_workspace(db, workspace_id, user, "viewer")
    query = db.query(UsageRecord).filter(UsageRecord.workspace_id == workspace_id)
    if metric:
        query = query.filter(UsageRecord.metric == metric)
    records = query.order_by(UsageRecord.recorded_at.desc()).all()
    return [UsageRecordOut.model_validate(record) for record in records]


@router.get(
    "/workspaces/{workspace_id}/usage/summary",
    response_model=list[UsageSummaryOut],
    status_code=status.HTTP_200_OK,
)
def usage_summary(
    workspace_id: str,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[UsageSummaryOut]:
    """Per-metric totals for dashboard and quota reporting."""
    _authorize_workspace(db, workspace_id, user, "viewer")
    rows = (
        db.query(UsageRecord.metric, func.sum(UsageRecord.quantity))
        .filter(UsageRecord.workspace_id == workspace_id)
        .group_by(UsageRecord.metric)
        .order_by(UsageRecord.metric)
        .all()
    )
    return [
        UsageSummaryOut(metric=metric, quantity=float(quantity or 0.0))
        for metric, quantity in rows
    ]