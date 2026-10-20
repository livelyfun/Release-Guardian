from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import IdMixin, TimestampMixin, utcnow


class Deployment(IdMixin, TimestampMixin, Base):
    __tablename__ = "deployments"

    environment_id: Mapped[str] = mapped_column(
        ForeignKey("environments.id", ondelete="CASCADE"), index=True
    )
    commit_sha: Mapped[str] = mapped_column(String(64), index=True)
    branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pull_request: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)


class Incident(IdMixin, TimestampMixin, Base):
    __tablename__ = "incidents"

    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    environment_id: Mapped[str | None] = mapped_column(
        ForeignKey("environments.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(300))
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    dedupe_key: Mapped[str] = mapped_column(String(255), index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list["IncidentEvent"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )


class IncidentEvent(IdMixin, TimestampMixin, Base):
    __tablename__ = "incident_events"

    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(String(1000))
    meta: Mapped[dict] = mapped_column(JSON, default=dict)

    incident: Mapped["Incident"] = relationship(back_populates="events")


class NotificationChannel(IdMixin, TimestampMixin, Base):
    __tablename__ = "notification_channels"

    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(30), default="webhook")
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class NotificationAttempt(IdMixin, TimestampMixin, Base):
    __tablename__ = "notification_attempts"

    channel_id: Mapped[str] = mapped_column(
        ForeignKey("notification_channels.id", ondelete="CASCADE"), index=True
    )
    incident_id: Mapped[str | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    subject: Mapped[str | None] = mapped_column(String(300), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class UsageRecord(IdMixin, TimestampMixin, Base):
    __tablename__ = "usage_records"

    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    metric: Mapped[str] = mapped_column(String(80), index=True)
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
