from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.base import utcnow
from app.models.execution import Baseline, Run
from app.models.project import Monitor

METRIC = "duration_ms"
DEFAULT_TOLERANCE = 0.5
MIN_SAMPLES = 3


def update_baseline(db: Session, monitor: Monitor, duration_ms: int) -> Baseline:
    baseline = (
        db.query(Baseline)
        .filter(Baseline.monitor_id == monitor.id, Baseline.metric == METRIC)
        .one_or_none()
    )
    if baseline is None:
        baseline = Baseline(monitor_id=monitor.id, metric=METRIC, value=float(duration_ms), sample_count=1)
        db.add(baseline)
        return baseline

    total = baseline.value * baseline.sample_count + duration_ms
    baseline.sample_count += 1
    baseline.value = total / baseline.sample_count
    baseline.updated_at = utcnow()
    return baseline


def evaluate_regression(db: Session, monitor: Monitor, duration_ms: int) -> dict:
    baseline = (
        db.query(Baseline)
        .filter(Baseline.monitor_id == monitor.id, Baseline.metric == METRIC)
        .one_or_none()
    )
    if baseline is None or baseline.sample_count < MIN_SAMPLES:
        return {"regression": False, "insufficient_baseline": True}

    config = monitor.config or {}
    tolerance = float(config.get("regression_tolerance", DEFAULT_TOLERANCE))
    threshold = baseline.value * (1 + tolerance)
    return {
        "regression": duration_ms > threshold,
        "baseline_ms": round(baseline.value, 2),
        "threshold_ms": round(threshold, 2),
        "actual_ms": duration_ms,
        "tolerance": tolerance,
        "samples": baseline.sample_count,
    }


def summarize(db: Session, monitor: Monitor, run: Run, duration_ms: int) -> dict:
    result = evaluate_regression(db, monitor, duration_ms)
    update_baseline(db, monitor, duration_ms)
    if run.summary is None:
        run.summary = {}
    run.summary["regression"] = result
    return result


def suppression_state(monitor: Monitor, now: datetime | None = None) -> dict | None:
    """Return the configured regression suppression, including expired ones."""
    config = monitor.config or {}
    raw = config.get("regression_suppressed_until")
    if not raw:
        return None
    try:
        until = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    current = now or datetime.now(UTC)
    return {
        "until": until.isoformat(),
        "reason": config.get("regression_suppression_reason") or "",
        "active": until > current,
    }


def active_suppression(monitor: Monitor, now: datetime | None = None) -> dict | None:
    state = suppression_state(monitor, now)
    if state is not None and state["active"]:
        return state
    return None
