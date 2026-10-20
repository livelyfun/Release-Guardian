from datetime import datetime

from sqlalchemy import Boolean, JSON, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import IdMixin, TimestampMixin, utcnow


class EscalationRule(IdMixin, TimestampMixin, Base):
    __tablename__ = "escalation_rules"
    __table_args__ = (UniqueConstraint("workspace_id", "name", name="uq_escalation_rule_ws_name"),)

    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    severity: Mapped[str] = mapped_column(String(20), default="medium")  # critical, high, medium, low
    minutes_to_escalate: Mapped[int] = mapped_column(Integer, default=30)  # minutes before next escalation
    channel_kind: Mapped[str] = mapped_column(String(30), default="webhook")  # webhook, email
    channel_config_key: Mapped[str | None] = mapped_column(String(100), nullable=True)  # config key e.g. "webhook_url"
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class AIConfiguration(IdMixin, TimestampMixin, Base):
    """Configuration for AI assistance settings per workspace."""
    __tablename__ = "ai_configurations"

    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, unique=True
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    model_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)  # openai, anthropic, google, etc.
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    temperature: Mapped[float] = mapped_column(default=0.0)
    max_tokens: Mapped[int | None] = mapped_column(default=None)
    redact_pii: Mapped[bool] = mapped_column(Boolean, default=True)
    confidence_threshold: Mapped[float] = mapped_column(default=0.8)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Run(IdMixin, TimestampMixin, Base):
    __tablename__ = "runs"

    monitor_id: Mapped[str] = mapped_column(ForeignKey("monitors.id", ondelete="CASCADE"), index=True)
    environment_id: Mapped[str] = mapped_column(
        ForeignKey("environments.id", ondelete="CASCADE"), index=True
    )
    deployment_id: Mapped[str | None] = mapped_column(
        ForeignKey("deployments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    trigger: Mapped[str] = mapped_column(String(30), default="manual")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)

    steps: Mapped[list["StepResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="StepResult.step_index"
    )


class StepResult(IdMixin, TimestampMixin, Base):
    __tablename__ = "step_results"

    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    step_index: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)

    run: Mapped["Run"] = relationship(back_populates="steps")


class Artifact(IdMixin, TimestampMixin, Base):
    __tablename__ = "artifacts"

    run_id: Mapped[str] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(30))  # screenshot | trace | harl | lighthouse
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)


class Baseline(IdMixin, TimestampMixin, Base):
    __tablename__ = "baselines"
    __table_args__ = (UniqueConstraint("monitor_id", "metric", name="uq_baseline_monitor_metric"),)

    monitor_id: Mapped[str] = mapped_column(ForeignKey("monitors.id", ondelete="CASCADE"), index=True)
    metric: Mapped[str] = mapped_column(String(80))
    value: Mapped[float] = mapped_column(Float)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
