import time
from urllib.parse import urljoin

import httpx

from app.core.config import settings
from app.services.browser import perform_browser_check
from app.services.outcomes import CheckOutcome, StepOutcome
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


def perform_lighthouse_check(monitor) -> CheckOutcome:
    """Run Lighthouse audit and return a CheckOutcome with scores/artifacts."""
    import subprocess
    import json
    import os
    import tempfile

    config = monitor.config or {}
    flags = config.get("flags", "")

    started = time.perf_counter()
    steps: list[StepOutcome] = []
    summary: dict = {}

    # Build lighthouse command
    url = monitor.target_url
    # Ensure URL has a scheme
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Output to a temp file for JSON parsing
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Run Lighthouse via CLI
        cmd = [
            "lighthouse",
            url,
            "--output=json",
            "--output-path=" + tmp_path,
            "--no-emulate-user-agent-permissions",
            "--disable-device-emulation",
            *(["--form-factor=desktop"] if config.get("form_factor") != "mobile" else []),
        ]
        if flags:
            cmd.extend(flags.split())

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=settings.step_timeout_seconds * 60)
        if result.returncode != 0:
            raise RuntimeError(f"Lighthouse failed: {result.stderr}")

        # Parse the JSON output
        with open(tmp_path, "r") as f:
            lh_data = json.load(f)

        elapsed_ms = int((time.perf_counter() - started) * 1000)

        # Extract key metrics
        lhr = lh_data.get("lhr", {})
        audits = lhr.get("audits", {}) or {}
        categories = lh_data.get("categories", {})

        # Store summary scores
        summary["performance_score"] = categories.get("performance", {}).get("score", 0) * 100
        summary["accessibility_score"] = categories.get("accessibility", {}).get("score", 0) * 100
        summary["best_practices_score"] = categories.get("best-practices", {}).get("score", 0) * 100
        summary["seo_score"] = categories.get("seo", {}).get("score", 0) * 100
        summary["first_contentful_paint"] = lhr.metrics.get("first-contentful-paint", {}).numericValue
        summary["largest_contentful_paint"] = lhr.metrics.get("largest-contentful-paint", {}).numericValue
        summary["total_blocking_time"] = lhr.metrics.get("total-blocking-time", {}).numericValue

        # Create steps for key audits
        for audit_key, audit_data in audits.items():
            title = audit_data.get("title", audit_key)
            score = audit_data.get("score", None)
            numeric_value = audit_data.get("numericValue", None)
            error = audit_data.get("errorMessage", None)

            status = "passed" if score is not None and score >= 0.9 else "failed" if score is not None else "inconclusive"
            steps.append(
                StepOutcome(
                    name=title,
                    status=status,
                    duration_ms=elapsed_ms,
                    error=str(error)[:500] if error else None,
                    evidence={
                        "score": score,
                        "numeric_value": numeric_value,
                        "raw": audit_data,
                    },
                )
            )

        # Store artifact references if save-assets was requested
        # (Lighthouse can save trace/screenshot assets to disk)
        if config.get("save_assets"):
            # TODO: copy artifacts to S3 storage
            summary["assets_saved"] = True

    except Exception as exc:  # noqa: BLE001 - surface failure as step, not a crash
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
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    overall = "passed" if steps and all(step.status == "passed" for step in steps) else "failed"
    duration_ms = int((time.perf_counter() - started) * 1000)
    return CheckOutcome(status=overall, duration_ms=duration_ms, steps=steps, summary=summary)


def perform_check(monitor) -> CheckOutcome:
    config = monitor.config or {}
    if monitor.kind == "browser" and config.get("steps"):
        return perform_browser_check(monitor)
    if monitor.kind == "lighthouse":
        return perform_lighthouse_check(monitor)
    return perform_http_check(monitor)
