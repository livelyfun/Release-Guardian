"""Dependency-free Prometheus metrics registry.

A small subset of the Prometheus client API is implemented so the control
plane exposes ``/metrics`` without adding a runtime dependency.  Metrics are
process-local; with multiple API workers each replica exposes its own series
and Prometheus aggregates them.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from collections.abc import Iterable

_lock = threading.Lock()


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _labels_to_text(labels: dict[str, str]) -> str:
    if not labels:
        return ""
    parts = [f'{key}="{_escape(str(value))}"' for key, value in sorted(labels.items())]
    return "{" + ",".join(parts) + "}"


class _Metric:
    type_name = "untyped"
    help_text = ""

    def __init__(self, name: str, help_text: str = "", labelnames: Iterable[str] = ()) -> None:
        self.name = name
        self.help_text = help_text or name
        self.labelnames = tuple(labelnames)

    def _key(self, labels: dict[str, str]) -> tuple:
        return tuple(sorted((key, str(value)) for key, value in labels.items()))

    def render(self) -> str:
        raise NotImplementedError


class Counter(_Metric):
    type_name = "counter"

    def __init__(self, name: str, help_text: str = "", labelnames: Iterable[str] = ()) -> None:
        super().__init__(name, help_text, labelnames)
        self._values: dict[tuple, float] = defaultdict(float)

    def labels(self, **labels: str) -> Counter:
        parent = self

        class _Child:
            def inc(self, amount: float = 1.0) -> None:
                parent.inc(amount, **labels)

        return _Child()  # type: ignore[return-value]

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        with _lock:
            self._values[self._key(labels)] += amount

    def render(self) -> str:
        lines = [f"# HELP {self.name} {self.help_text}", f"# TYPE {self.name} {self.type_name}"]
        for key, value in sorted(self._values.items()):
            labels = dict(key)
            lines.append(f"{self.name}{_labels_to_text(labels)} {value:g}")
        return "\n".join(lines)


class Gauge(_Metric):
    type_name = "gauge"

    def __init__(self, name: str, help_text: str = "", labelnames: Iterable[str] = ()) -> None:
        super().__init__(name, help_text, labelnames)
        self._values: dict[tuple, float] = defaultdict(float)

    def set(self, value: float, **labels: str) -> None:
        with _lock:
            self._values[self._key(labels)] = value

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        with _lock:
            self._values[self._key(labels)] += amount

    def dec(self, amount: float = 1.0, **labels: str) -> None:
        with _lock:
            self._values[self._key(labels)] -= amount

    def render(self) -> str:
        lines = [f"# HELP {self.name} {self.help_text}", f"# TYPE {self.name} {self.type_name}"]
        for key, value in sorted(self._values.items()):
            lines.append(f"{self.name}{_labels_to_text(dict(key))} {value:g}")
        return "\n".join(lines)


class Histogram(_Metric):
    type_name = "histogram"
    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)

    def __init__(
        self,
        name: str,
        help_text: str = "",
        labelnames: Iterable[str] = (),
        buckets: Iterable[float] | None = None,
    ) -> None:
        super().__init__(name, help_text, labelnames)
        self.buckets = tuple(buckets or self.DEFAULT_BUCKETS)
        self._counts: dict[tuple, list[int]] = {}
        self._sums: dict[tuple, float] = defaultdict(float)
        self._totals: dict[tuple, int] = defaultdict(int)

    def labels(self, **labels: str) -> _HistogramChild:
        return _HistogramChild(self, labels)

    def observe(self, value: float, **labels: str) -> None:
        key = self._key(labels)
        with _lock:
            counts = self._counts.get(key)
            if counts is None:
                counts = [0] * len(self.buckets)
                self._counts[key] = counts
            for index, boundary in enumerate(self.buckets):
                if value <= boundary:
                    counts[index] += 1
            self._sums[key] += value
            self._totals[key] += 1

    def render(self) -> str:
        lines = [f"# HELP {self.name} {self.help_text}", f"# TYPE {self.name} {self.type_name}"]
        for key, counts in sorted(self._counts.items()):
            labels = dict(key)
            for index, boundary in enumerate(self.buckets):
                bucket_labels = {**labels, "le": str(boundary)}
                lines.append(f"{self.name}_bucket{_labels_to_text(bucket_labels)} {counts[index]}")
            total_labels = {**labels, "le": "+Inf"}
            lines.append(f"{self.name}_bucket{_labels_to_text(total_labels)} {self._totals[key]}")
            lines.append(f"{self.name}_sum{_labels_to_text(labels)} {self._sums[key]:g}")
            lines.append(f"{self.name}_count{_labels_to_text(labels)} {self._totals[key]}")
        return "\n".join(lines)


class _HistogramChild:
    def __init__(self, parent: Histogram, labels: dict[str, str]) -> None:
        self._parent = parent
        self._labels = labels

    def observe(self, value: float) -> None:
        self._parent.observe(value, **self._labels)


_REGISTRY: list[_Metric] = []


def _register(metric: _Metric) -> _Metric:
    _REGISTRY.append(metric)
    return metric


def render_metrics() -> str:
    with _lock:
        blocks = [metric.render() for metric in _REGISTRY]
    return "\n".join(blocks) + "\n"


# --- Release Guardian metric definitions ------------------------------------

API_REQUESTS = _register(
    Counter(
        "rg_api_requests_total",
        "HTTP API requests by method, route and status.",
        ("method", "route", "status"),
    )
)
API_LATENCY = _register(
    Histogram(
        "rg_api_request_duration_seconds",
        "HTTP API request latency in seconds.",
        ("method", "route"),
    )
)
RUNS_TOTAL = _register(
    Counter(
        "rg_runs_total",
        "Executed runs by monitor kind and terminal status.",
        ("kind", "status"),
    )
)
RUN_DURATION = _register(
    Histogram(
        "rg_run_duration_seconds",
        "Run duration in seconds by monitor kind.",
        ("kind",),
    )
)
SCHEDULER_ENQUEUED = _register(
    Counter("rg_scheduler_enqueued_total", "Runs enqueued by the due-monitor scheduler.")
)
ARTIFACT_UPLOADS = _register(
    Counter(
        "rg_artifact_uploads_total",
        "Artifact upload attempts by kind and result.",
        ("kind", "status"),
    )
)
NOTIFICATION_ATTEMPTS = _register(
    Counter(
        "rg_notification_attempts_total",
        "Notification delivery attempts by channel and result.",
        ("channel", "status"),
    )
)
BLOCKED_URLS = _register(
    Counter(
        "rg_blocked_urls_total",
        "SSRF URL validations rejected.",
        ("reason",),
    )
)
ACTIVE_RUNS = _register(
    Gauge("rg_active_runs", "Runs currently executing in this process.", ("kind",))
)
STALE_RUNS = _register(
    Counter(
        "rg_stale_runs_total",
        "Stale runs handled by the maintenance sweeper.",
        ("action",),
    )
)
SCHEDULER_LAST_SUCCESS = _register(
    Gauge(
        "rg_scheduler_last_success_timestamp_seconds",
        "Unix timestamp of the last successful due-monitor scheduler tick.",
    )
)
SWEEPER_LAST_SUCCESS = _register(
    Gauge(
        "rg_sweeper_last_success_timestamp_seconds",
        "Unix timestamp of the last successful stale-run sweep.",
    )
)
QUEUE_DEPTH = _register(
    Gauge("rg_queue_depth", "Approximate number of queued Celery tasks.")
)
PENDING_RUNS = _register(Gauge("rg_pending_runs", "Runs currently in pending state."))
OLDEST_PENDING_RUN_AGE = _register(
    Gauge(
        "rg_oldest_pending_run_age_seconds",
        "Age in seconds of the oldest pending run (0 when the queue is empty).",
    )
)
ESCALATIONS = _register(
    Counter(
        "rg_escalations_total",
        "Incident escalation attempts by delivery status.",
        ("status",),
    )
)
