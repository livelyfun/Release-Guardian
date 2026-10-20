from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.v1.deps import Principal, get_principal, require_role
from app.core.database import get_db
from app.models.base import utcnow
from app.models.release import Incident, IncidentEvent
from app.schemas.release import IncidentOut, IncidentUpdate
from app.services import audit
from app.services.export import csv_response

router = APIRouter(tags=["incidents"])


def _authorize_incident(db: Session, incident_id: str, user: Principal) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    require_role(db, incident.workspace_id, user, "viewer")
    return incident


@router.get("/incidents", response_model=list[IncidentOut])
def list_incidents(
    workspace_id: str = Query(...),
    status_filter: str | None = Query(default=None, alias="status"),
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[IncidentOut]:
    require_role(db, workspace_id, user, "viewer")
    query = db.query(Incident).filter(Incident.workspace_id == workspace_id)
    if status_filter:
        query = query.filter(Incident.status == status_filter)
    incidents = query.order_by(Incident.opened_at.desc()).all()
    return [IncidentOut.model_validate(incident) for incident in incidents]


@router.get("/incidents/export.csv")
def export_incidents(
    workspace_id: str = Query(...),
    status_filter: str | None = Query(default=None, alias="status"),
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> Response:
    require_role(db, workspace_id, user, "viewer")
    query = db.query(Incident).filter(Incident.workspace_id == workspace_id)
    if status_filter:
        query = query.filter(Incident.status == status_filter)
    incidents = query.order_by(Incident.opened_at.desc()).all()
    return csv_response(
        [
            "id",
            "title",
            "severity",
            "status",
            "project_id",
            "environment_id",
            "dedupe_key",
            "opened_at",
            "acknowledged_at",
            "resolved_at",
        ],
        [
            [
                incident.id,
                incident.title,
                incident.severity,
                incident.status,
                incident.project_id,
                incident.environment_id,
                incident.dedupe_key,
                incident.opened_at.isoformat() if incident.opened_at else None,
                incident.acknowledged_at.isoformat() if incident.acknowledged_at else None,
                incident.resolved_at.isoformat() if incident.resolved_at else None,
            ]
            for incident in incidents
        ],
        "incidents.csv",
    )


@router.get("/incidents/{incident_id}", response_model=IncidentOut)
def get_incident(
    incident_id: str,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> IncidentOut:
    incident = _authorize_incident(db, incident_id, user)
    return IncidentOut.model_validate(incident)


@router.patch("/incidents/{incident_id}", response_model=IncidentOut)
def update_incident(
    incident_id: str,
    payload: IncidentUpdate,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> IncidentOut:
    incident = _authorize_incident(db, incident_id, user)
    require_role(db, incident.workspace_id, user, "developer")

    if payload.severity:
        incident.severity = payload.severity
    if payload.status:
        incident.status = payload.status
        if payload.status == "acknowledged":
            incident.acknowledged_at = utcnow()
        elif payload.status == "resolved":
            incident.resolved_at = utcnow()
        db.add(
            IncidentEvent(
                incident_id=incident.id,
                type=f"status:{payload.status}",
                message=f"Status changed to {payload.status}",
            )
        )

    audit.record(
        db,
        action="incident.update",
        target_type="incident",
        workspace_id=incident.workspace_id,
        user_id=user.id,
        target_id=incident.id,
        meta=payload.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(incident)
    return IncidentOut.model_validate(incident)
