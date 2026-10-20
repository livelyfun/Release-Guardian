import time
from urllib.parse import urljoin

import httpx

from app.core.config import settings
from app.services.browser import perform_browser_check
from app.services.outcomes import CheckOutcome, StepOutcome
from app.services.storage import upload_bytes
from app.services.url_guard import validate_url

__all__ = ["CheckOutcome", "StepOutcome", "perform_check", "perform_http_check", "perform_lighthouse_check"]


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


def _failure(name: str, error: str, started: float) -> CheckOutcome:
    duration_ms = int((time.perf_counter() - started) * 1000)
    return CheckOutcome(
        status="failed",
        duration_ms=duration_ms,
        steps=[
            StepOutcome(name=name, status="failed", duration_ms=duration_ms, error=error[:2000])
        ],
        summary={"error": error[:500]},
    )


def perform_lighthouse_check(monitor, run_id: str | None = None) -> CheckOutcome:
    """Run a Lighthouse audit and return scores plus an optional report artifact."""
    import json
    import os
    import subprocess
    import tempfile

    config = monitor.config or {}
    flags = config.get("flags", "")

    started = time.perf_counter()
    steps: list[StepOutcome] = []
    summary: dict = {}

    url = monitor.target_url
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        validate_url(url, settings.allow_private_urls)
    except Exception as exc:  # noqa: BLE001 - never launch a browser at a blocked target
        return _failure("Target validation", str(exc), started)

    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        cmd = [
            "lighthouse",
            url,
            "--quiet",
            "--output=json",
            "--output-path=" + tmp_path,
            "--chrome-flags=--headless --no-sandbox --disable-dev-shm-usage",
        ]
        if config.get("form_factor") != "mobile":
            cmd.append("--preset=desktop")
        if flags:
            cmd.extend(flags.split())

        timeout_seconds = int(
            config.get("timeout_seconds") or max(60, settings.step_timeout_seconds * 2)
        )
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout_seconds, check=False
        )
        if result.returncode != 0:
            raise RuntimeError(f"Lighthouse exited {result.returncode}: {result.stderr[:1000]}")

        with open(tmp_path, encoding="utf-8") as report_file:
            report = json.load(report_file)

        runtime_error = report.get("runtimeError")
        if runtime_error:
            code = runtime_error.get("code") if isinstance(runtime_error, dict) else None
            message = runtime_error.get("message") if isinstance(runtime_error, dict) else None
            raise RuntimeError(f"Lighthouse runtime error {code}: {message}")

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        categories = report.get("categories") or {}
        audits = report.get("audits") or {}
        if not categories:
            raise RuntimeError("Lighthouse report contained no categories")

        min_scores = {
            str(key): float(value) for key, value in (config.get("min_scores") or {}).items()
        }
        scores: dict[str, float | None] = {}
        for key, category in categories.items():
            raw_score = category.get("score") if isinstance(category, dict) else None
            score = round(raw_score * 100, 1) if raw_score is not None else None
            scores[key] = score
            minimum = min_scores.get(key)
            if score is None:
                status = "inconclusive"
                error = "Lighthouse did not produce a score"
            elif minimum is not None and score < minimum:
                status = "failed"
                error = f"Score {score} below minimum {minimum}"
            else:
                status = "passed"
                error = None
            steps.append(
                StepOutcome(
                    name=category.get("title", key) if isinstance(category, dict) else key,
                    status=status,
                    duration_ms=elapsed_ms,
                    error=error,
                    evidence={"score": score, "minimum": minimum},
                )
            )

        summary["scores"] = scores
        summary["performance_score"] = scores.get("performance")
        summary["accessibility_score"] = scores.get("accessibility")
        summary["best_practices_score"] = scores.get("best-practices")
        summary["seo_score"] = scores.get("seo")
        for audit_key, summary_key in (
            ("first-contentful-paint", "first_contentful_paint"),
            ("largest-contentful-paint", "largest_contentful_paint"),
            ("total-blocking-time", "total_blocking_time"),
            ("cumulative-layout-shift", "cumulative_layout_shift"),
            ("speed-index", "speed_index"),
        ):
            audit = audits.get(audit_key) or {}
            summary[summary_key] = audit.get("numericValue")

        if config.get("save_assets"):
            try:
                artifact = upload_bytes(
                    run_id=run_id or monitor.id,
                    kind="lighthouse",
                    data=json.dumps(report).encode(),
                    mime_type="application/json",
                    extension="json",
                )
                summary["report_url"] = artifact["url"]
                summary["report_key"] = artifact["storage_key"]
            except Exception as exc:  # noqa: BLE001 - report storage is best-effort
                summary["report_error"] = str(exc)[:300]

    except Exception as exc:  # noqa: BLE001 - surface failure as a step, not a crash
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        steps.append(
            StepOutcome(
                name="Lighthouse audit",
                status="failed",
                duration_ms=elapsed_ms,
                error=str(exc)[:2000],
            )
        )
        summary["error"] = str(exc)[:500]
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    overall = "passed" if steps and all(step.status == "passed" for step in steps) else "failed"
    duration_ms = int((time.perf_counter() - started) * 1000)
    return CheckOutcome(status=overall, duration_ms=duration_ms, steps=steps, summary=summary)


def perform_check(monitor, run_id: str | None = None) -> CheckOutcome:
    if monitor.kind == "browser":
        return perform_browser_check(monitor, run_id=run_id)
    if monitor.kind == "lighthouse":
        return perform_lighthouse_check(monitor, run_id=run_id)
    return perform_http_check(monitor)
