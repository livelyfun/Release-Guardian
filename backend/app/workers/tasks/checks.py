import logging

from app.core.database import SessionLocal
from app.core.metrics import ACTIVE_RUNS, RUN_DURATION, RUNS_TOTAL
from app.models.base import utcnow
from app.models.execution import Artifact, Run, StepResult
from app.models.project import Environment, Monitor, Project
from app.models.release import UsageRecord
from app.services.checks import perform_check
from app.services.incidents import (
    open_or_refresh_incident,
    open_regression_incident,
    resolve_open_incidents,
)
from app.services.notifications import dispatch as notification_dispatch
from app.services.regression import summarize as summarize_regression
from app.services.runs import refresh_deployment_status

logger = logging.getLogger("release_guardian.worker")


def _record_artifact(db, run: Run, outcome) -> None:
    """Persist artifact metadata for a run when the check produced one."""
    storage_key = outcome.summary.get("screenshot_key")
    if not storage_key:
        return
    existing = db.query(Artifact).filter(Artifact.storage_key == storage_key).one_or_none()
    if existing is not None:
        return
    db.add(
        Artifact(
            run_id=run.id,
            kind="screenshot",
            storage_key=storage_key,
            url=outcome.summary.get("screenshot_url"),
            size_bytes=outcome.summary.get("screenshot_size_bytes"),
            mime_type="image/png",
        )
    )


def execute_run(run_id: str) -> dict:
    db = SessionLocal()
    active_kind: str | None = None
    try:
        run = db.get(Run, run_id)
        if run is None:
            return {"run_id": run_id, "status": "not_found"}

        monitor = db.get(Monitor, run.monitor_id)
        if monitor is None:
            run.status = "inconclusive"
            run.summary = {"error": "monitor missing"}
            if run.deployment_id is not None:
                refresh_deployment_status(db, run.deployment_id)
            db.commit()
            RUNS_TOTAL.inc(kind="unknown", status="inconclusive")
            return {"run_id": run_id, "status": "inconclusive"}

        environment = db.get(Environment, monitor.environment_id)
        project = db.get(Project, environment.project_id) if environment else None

        run.status = "running"
        run.started_at = utcnow()
        db.commit()

        active_kind = monitor.kind
        ACTIVE_RUNS.inc(kind=active_kind)
        try:
            outcome = perform_check(monitor, run_id=run.id)
        finally:
            ACTIVE_RUNS.dec(kind=active_kind)

        RUNS_TOTAL.inc(kind=monitor.kind, status=outcome.status)
        RUN_DURATION.observe(outcome.duration_ms / 1000.0, kind=monitor.kind)

        for index, step in enumerate(outcome.steps):
            db.add(
                StepResult(
                    run_id=run.id,
                    step_index=index,
                    name=step.name,
                    status=step.status,
                    duration_ms=step.duration_ms,
                    error=step.error,
                    evidence=step.evidence,
                )
            )

        run.status = outcome.status
        run.duration_ms = outcome.duration_ms
        run.finished_at = utcnow()
        run.summary = outcome.summary
        # Attach artifact URLs from the check outcome
        if outcome.summary.get("screenshot_url"):
            run.summary["screenshot_url"] = outcome.summary["screenshot_url"]
        if outcome.summary.get("screenshot_key"):
            run.summary["screenshot_key"] = outcome.summary["screenshot_key"]
        _record_artifact(db, run, outcome)
        monitor.last_checked_at = run.finished_at

        opened_incidents = []
        resolved_incidents = []
        if project is not None and environment is not None:
            # Track usage per check type
            metric = "runs"
            if monitor.kind == "lighthouse":
                metric = "lighthouse_checks"
            elif monitor.kind == "browser":
                metric = "browser_checks"
            db.add(UsageRecord(workspace_id=project.workspace_id, metric=metric, quantity=1.0))
            if outcome.status == "failed":
                reason = outcome.steps[-1].error or "Check failed"
                incident, created = open_or_refresh_incident(
                    db, run, monitor, environment, project, reason
                )
                if created:
                    opened_incidents.append(incident)
            else:
                resolved_incidents += resolve_open_incidents(db, f"monitor:{monitor.id}:failure")

                regression = summarize_regression(db, monitor, run, outcome.duration_ms)
                if regression.get("regression"):
                    incident, created = open_regression_incident(
                        db,
                        run,
                        monitor,
                        environment,
                        project,
                        regression["actual_ms"],
                        regression["baseline_ms"],
                        regression["threshold_ms"],
                    )
                    if created:
                        opened_incidents.append(incident)
                else:
                    resolved_incidents += resolve_open_incidents(
                        db, f"monitor:{monitor.id}:regression"
                    )

        if run.deployment_id is not None:
            refresh_deployment_status(db, run.deployment_id)

        db.commit()

        for incident in opened_incidents:
            notification_dispatch.incident_opened(db, incident)
        for incident in resolved_incidents:
            notification_dispatch.incident_resolved(db, incident)

        logger.info(
            "run_completed",
            extra={
                "run_id": run.id,
                "monitor_id": monitor.id,
                "kind": monitor.kind,
                "status": run.status,
                "duration_ms": run.duration_ms,
            },
        )
        return {"run_id": run.id, "status": run.status}
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        run = db.get(Run, run_id)
        if run is not None:
            run.status = "inconclusive"
            run.finished_at = utcnow()
            run.summary = {"error": str(exc)[:500]}
            if run.deployment_id is not None:
                refresh_deployment_status(db, run.deployment_id)
            db.commit()
        RUNS_TOTAL.inc(kind=active_kind or "unknown", status="inconclusive")
        logger.exception("run_failed", extra={"run_id": run_id})
        return {"run_id": run_id, "status": "error", "error": str(exc)[:500]}
    finally:
        db.close()
