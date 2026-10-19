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
