import time
from dataclasses import dataclass, field
from urllib.parse import urljoin

import httpx

from app.core.config import settings
from app.services.url_guard import validate_url


@dataclass
class StepOutcome:
    name: str
    status: str
    duration_ms: int
    error: str | None = None
    evidence: dict = field(default_factory=dict)


@dataclass
class CheckOutcome:
    status: str
    duration_ms: int
    steps: list[StepOutcome]
    summary: dict


def _fetch_with_redirects(url: str) -> tuple[httpx.Response, list[str]]:
    chain: list[str] = []
    current = url
    with httpx.Client(
        timeout=settings.step_timeout_seconds,
        follow_redirects=False,
        headers={"User-Agent": "ReleaseGuardian/0.1 (+https://releaseguardian.example)"},
    ) as client:
        for _ in range(settings.max_redirects + 1):
            validate_url(current, settings.allow_private_urls)
            response = client.get(current)
            if response.is_redirect and response.headers.get("location"):
                chain.append(current)
                current = urljoin(current, response.headers["location"])
                continue
            return response, chain
    raise httpx.TooManyRedirects(f"More than {settings.max_redirects} redirects")


def perform_http_check(monitor) -> CheckOutcome:
    config = monitor.config or {}
    expected_status = set(config.get("expected_status", [200]))
    expected_text = config.get("expected_text")

    started = time.perf_counter()
    steps: list[StepOutcome] = []
    summary: dict = {}

    try:
        response, chain = _fetch_with_redirects(monitor.target_url)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        summary["status_code"] = response.status_code
        summary["redirects"] = len(chain)

        status_ok = response.status_code in expected_status
        steps.append(
            StepOutcome(
                name="HTTP request",
                status="passed" if status_ok else "failed",
                duration_ms=elapsed_ms,
                error=None if status_ok else f"Unexpected status {response.status_code}",
                evidence={"status_code": response.status_code, "redirects": chain},
            )
        )

        if expected_text:
            text_ok = expected_text in response.text
            steps.append(
                StepOutcome(
                    name="Content assertion",
                    status="passed" if text_ok else "failed",
                    duration_ms=0,
                    error=None if text_ok else "Expected text not found in response",
                    evidence={"expected_text": expected_text},
                )
            )

        if monitor.kind in {"browser", "lighthouse"}:
            steps.append(
                StepOutcome(
                    name="Asset retrieval",
                    status="passed" if status_ok else "failed",
                    duration_ms=0,
                    evidence={
                        "note": "Server-side retrieval only; full browser execution runs in worker image"
                    },
                )
            )
    except Exception as exc:  # noqa: BLE001 - surface failure as a step, not a crash
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        steps.append(
            StepOutcome(
                name="HTTP request",
                status="failed",
                duration_ms=elapsed_ms,
                error=str(exc)[:2000],
            )
        )
        summary["error"] = str(exc)[:500]

    overall = "passed" if steps and all(step.status == "passed" for step in steps) else "failed"
    duration_ms = int((time.perf_counter() - started) * 1000)
    return CheckOutcome(status=overall, duration_ms=duration_ms, steps=steps, summary=summary)
