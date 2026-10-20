from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import Principal, get_principal, require_role
from app.core.database import get_db
from app.models.execution import EscalationRule
from app.schemas.release import (
    EscalationRuleCreate,
    EscalationRuleOut,
    EscalationRuleUpdate,
    _ChannelConfig,
)
from app.services import audit

router = APIRouter(tags=["escalations"])


def _authorize_rule(
    db: Session, rule_id: str, user: Principal, role: str
) -> EscalationRule:
    rule = db.get(EscalationRule, rule_id)
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Escalation rule not found"
        )
    require_role(db, rule.workspace_id, user, role)
    return rule


@router.get(
    "/workspaces/{workspace_id}/escalation-rules",
    response_model=list[EscalationRuleOut],
)
def list_escalation_rules(
    workspace_id: str,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[EscalationRuleOut]:
    require_role(db, workspace_id, user, "viewer")
    rules = (
        db.query(EscalationRule)
        .filter(EscalationRule.workspace_id == workspace_id)
        .order_by(EscalationRule.severity, EscalationRule.minutes_to_escalate)
        .all()
    )
    return [EscalationRuleOut.model_validate(rule) for rule in rules]


@router.post(
    "/workspaces/{workspace_id}/escalation-rules",
    response_model=EscalationRuleOut,
    status_code=status.HTTP_201_CREATED,
)
def create_escalation_rule(
    workspace_id: str,
    payload: EscalationRuleCreate,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> EscalationRuleOut:
    require_role(db, workspace_id, user, "admin")
    existing = (
        db.query(EscalationRule)
        .filter(
            EscalationRule.workspace_id == workspace_id,
            EscalationRule.name == payload.name,
        )
        .one_or_none()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An escalation rule with this name already exists",
        )

    rule = EscalationRule(
        workspace_id=workspace_id,
        name=payload.name,
        severity=payload.severity,
        minutes_to_escalate=payload.minutes_to_escalate,
        channel_kind=payload.kind,
        channel_config=payload.config,
        is_enabled=payload.enabled,
    )
    db.add(rule)
    audit.record(
        db,
        action="escalation_rule.create",
        target_type="escalation_rule",
        workspace_id=workspace_id,
        user_id=user.id,
        target_id=rule.id,
        meta={
            "severity": rule.severity,
            "minutes_to_escalate": rule.minutes_to_escalate,
            "channel_kind": rule.channel_kind,
        },
    )
    db.commit()
    db.refresh(rule)
    return EscalationRuleOut.model_validate(rule)


@router.patch("/escalation-rules/{rule_id}", response_model=EscalationRuleOut)
def update_escalation_rule(
    rule_id: str,
    payload: EscalationRuleUpdate,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> EscalationRuleOut:
    rule = _authorize_rule(db, rule_id, user, "admin")

    kind = payload.kind or rule.channel_kind
    config = payload.config if payload.config is not None else rule.channel_config
    _ChannelConfig(kind=kind, config=config)

    if payload.name is not None:
        rule.name = payload.name
    if payload.severity is not None:
        rule.severity = payload.severity
    if payload.minutes_to_escalate is not None:
        rule.minutes_to_escalate = payload.minutes_to_escalate
    rule.channel_kind = kind
    rule.channel_config = config
    if payload.enabled is not None:
        rule.is_enabled = payload.enabled

    audit.record(
        db,
        action="escalation_rule.update",
        target_type="escalation_rule",
        workspace_id=rule.workspace_id,
        user_id=user.id,
        target_id=rule.id,
        meta=payload.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(rule)
    return EscalationRuleOut.model_validate(rule)


@router.delete(
    "/escalation-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_escalation_rule(
    rule_id: str,
    user: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> None:
    rule = _authorize_rule(db, rule_id, user, "admin")
    audit.record(
        db,
        action="escalation_rule.delete",
        target_type="escalation_rule",
        workspace_id=rule.workspace_id,
        user_id=user.id,
        target_id=rule.id,
    )
    db.delete(rule)
    db.commit()
