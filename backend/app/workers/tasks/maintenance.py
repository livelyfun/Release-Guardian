"""Maintenance sweeper for lost or stuck runs.

Celery with acknowledgements-after-execution plus a single worker can still
leave work behind: a broker publish can fail after the Run row is committed, or
a worker can die mid-execution.  The sweeper re-dispatches old pending runs and
marks over-time running runs inconclusive so deployment status does not hang
forever.  It is safe to run from multiple schedulers: re-dispatch is guarded by
the same active-run rules, and terminal updates are idempotent.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.metrics import STALE_RUNS
from app.models.base import utcnow
from app.models.execution import Run
from app.services.runs import refresh_deployment_status
from app.workers.dispatch import dispatch_run

logger = logging.getLogger("release_guardian.maintenance")


def sweep_stale_runs(db: Session | None = None) -> dict:
    owned = db is None
    session = db or SessionLocal()
    now = utcnow()
    redispatched: list[str] = []
    timed_out: list[str] = []
    dispatch_failures: list[str] = []

    try:
        pending_cutoff = now - timedelta(seconds=settings.pending_run_timeout_seconds)
        pending_runs = (
            session.query(Run)
            .filter(Run.status == "pending", Run.created_at < pending_cutoff)
            .order_by(Run.created_at)
            .limit(settings.stale_run_sweep_batch)
            .all()
        )
        for run in pending_runs:
            try:
                dispatch_run(run.id)
                redispatched.append(run.id)
                STALE_RUNS.inc(action="redispatched")
            except Exception as exc:  # noqa: BLE001 - try again on the next sweep
                dispatch_failures.append(run.id)
                logger.warning(
                    "stale_run_redispatch_failed",
                    extra={"run_id": run.id, "error": str(exc)[:200]},
                )

        running_cutoff = now - timedelta(seconds=settings.run_timeout_seconds + 60)
        running_runs = (
            session.query(Run)
            .filter(Run.status == "running", Run.started_at < running_cutoff)
            .order_by(Run.started_at)
            .limit(settings.stale_run_sweep_batch)
            .all()
        )
        for run in running_runs:
            run.status = "inconclusive"
            run.finished_at = now
            run.summary = {
                **(run.summary or {}),
                "error": f"Run exceeded {settings.run_timeout_seconds}s and was marked inconclusive",
            }
            timed_out.append(run.id)
            STALE_RUNS.inc(action="timed_out")
            if run.deployment_id is not None:
                refresh_deployment_status(session, run.deployment_id)

        session.commit()
    finally:
        if owned:
            session.close()

    if redispatched or timed_out or dispatch_failures:
        logger.info(
            "stale_run_sweep",
            extra={
                "redispatched": len(redispatched),
                "timed_out": len(timed_out),
                "dispatch_failures": len(dispatch_failures),
            },
        )

    return {
        "redispatched": redispatched,
        "timed_out": timed_out,
        "dispatch_failures": dispatch_failures,
    }
