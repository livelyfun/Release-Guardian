import hashlib
import time
from urllib.parse import urljoin, urlparse

from app.core.config import settings
from app.core.metrics import BLOCKED_URLS
from app.services.outcomes import CheckOutcome, StepOutcome
from app.services.storage import upload_bytes
from app.services.url_guard import validate_url

SUPPORTED_ACTIONS = {
    "goto",
    "click",
    "fill",
    "select",
    "press",
    "expect_text",
    "expect_visible",
    "expect_url",
    "wait",
    "screenshot",
}

MAX_STEPS = 50


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


def perform_browser_check(monitor, run_id: str | None = None) -> CheckOutcome:
    config = monitor.config or {}
    steps = config.get("steps") or []
    started = time.perf_counter()

    if not steps:
        return _failure("Browser journey", "No browser steps configured", started)
    if len(steps) > MAX_STEPS:
        return _failure("Browser journey", f"Too many steps (max {MAX_STEPS})", started)

    for step in steps:
        if step.get("action") not in SUPPORTED_ACTIONS:
            return _failure(
                "Browser journey",
                f"Unsupported action: {step.get('action')}",
                started,
            )

    try:
        validate_url(monitor.target_url, settings.allow_private_urls)
    except Exception as exc:  # noqa: BLE001 - reject disallowed targets before launch
        return _failure("Target validation", str(exc), started)

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # noqa: BLE001
        return _failure("Browser launch", f"Playwright unavailable: {exc}", started)

    outcomes: list[StepOutcome] = []
    console_errors: list[str] = []
    failed_requests: list[str] = []
    blocked_requests: list[str] = []
    summary: dict = {}

    def guard_route(route) -> None:
        """Validate every browser request (navigations, XHR, subresources)."""
        request_url = route.request.url
        if urlparse(request_url).scheme in {"data", "blob", "about"}:
            route.continue_()
            return
        try:
            validate_url(request_url, settings.allow_private_urls)
        except Exception:  # noqa: BLE001 - abort anything that is not a public target
            blocked_requests.append(request_url)
            BLOCKED_URLS.inc(reason="browser_request")
            route.abort()
            return
        route.continue_()

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
            )
            context = browser.new_context()
            page = context.new_page()
            page.route("**/*", guard_route)
            page.set_default_timeout(settings.step_timeout_seconds * 1000)

            page.on(
                "console",
                lambda message: console_errors.append(message.text)
                if message.type == "error"
                else None,
            )
            page.on("requestfailed", lambda request: failed_requests.append(request.url))

            for step in steps:
                name = step.get("name") or step["action"]
                step_started = time.perf_counter()
                evidence: dict = {}
                try:
                    _run_step(page, monitor.target_url, step, evidence)
                    outcomes.append(
                        StepOutcome(
                            name=name,
                            status="passed",
                            duration_ms=int((time.perf_counter() - step_started) * 1000),
                            evidence=evidence,
                        )
                    )
                except Exception as exc:  # noqa: BLE001 - record failure as step evidence
                    outcomes.append(
                        StepOutcome(
                            name=name,
                            status="failed",
                            duration_ms=int((time.perf_counter() - step_started) * 1000),
                            error=str(exc)[:2000],
                            evidence=evidence,
                        )
                    )
                    break

            if config.get("check_console_errors") and console_errors:
                outcomes.append(
                    StepOutcome(
                        name="Console errors",
                        status="failed",
                        duration_ms=0,
                        error=f"{len(console_errors)} console error(s)",
                        evidence={"messages": console_errors[:20]},
                    )
                )
            if config.get("fail_on_request_failure") and failed_requests:
                outcomes.append(
                    StepOutcome(
                        name="Failed requests",
                        status="failed",
                        duration_ms=0,
                        error=f"{len(failed_requests)} request(s) failed",
                        evidence={"urls": failed_requests[:20]},
                    )
                )

            summary = {
                "final_url": page.url,
                "console_errors": console_errors[:20],
                "failed_requests": failed_requests[:20],
                "blocked_requests": blocked_requests[:20],
            }

            # Capture the real final page before closing the browser.  Artifact
            # failures are recorded as evidence and never fail the check.
            if config.get("capture_screenshot", True):
                try:
                    image = page.screenshot(full_page=True)
                    if image:
                        artifact = upload_bytes(
                            run_id=run_id or monitor.id,
                            kind="screenshot",
                            data=image,
                            mime_type="image/png",
                            extension="png",
                        )
                        summary["screenshot_url"] = artifact["url"]
                        summary["screenshot_key"] = artifact["storage_key"]
                        summary["screenshot_size_bytes"] = artifact["size_bytes"]
                except Exception as exc:  # noqa: BLE001 - artifact capture is best-effort
                    summary["screenshot_error"] = str(exc)[:300]

            context.close()
            browser.close()
    except Exception as exc:  # noqa: BLE001 - launch/navigation failures become evidence
        outcomes.append(
            StepOutcome(
                name="Browser execution",
                status="failed",
                duration_ms=int((time.perf_counter() - started) * 1000),
                error=str(exc)[:2000],
            )
        )
        summary = {"error": str(exc)[:500]}

    overall = "passed" if outcomes and all(step.status == "passed" for step in outcomes) else "failed"
    duration_ms = int((time.perf_counter() - started) * 1000)
    return CheckOutcome(
        status=overall, duration_ms=duration_ms, steps=outcomes, summary=summary
    )


def _run_step(page, base_url: str, step: dict, evidence: dict) -> None:
    action = step["action"]

    if action == "goto":
        target = urljoin(base_url.rstrip("/") + "/", step.get("url", ""))
        validate_url(target, settings.allow_private_urls)
        page.goto(target, wait_until=step.get("wait_until", "load"))
        evidence["url"] = page.url
    elif action == "click":
        page.click(step["selector"])
        evidence["selector"] = step["selector"]
    elif action == "fill":
        page.fill(step["selector"], str(step.get("value", "")))
        evidence["selector"] = step["selector"]
    elif action == "select":
        page.select_option(step["selector"], str(step.get("value", "")))
        evidence["selector"] = step["selector"]
    elif action == "press":
        page.press(step.get("selector") or "body", step.get("key", "Enter"))
    elif action == "expect_text":
        page.get_by_text(step["text"], exact=bool(step.get("exact", False))).first.wait_for()
        evidence["text"] = step["text"]
    elif action == "expect_visible":
        page.wait_for_selector(step["selector"], state="visible")
        evidence["selector"] = step["selector"]
    elif action == "expect_url":
        page.wait_for_url(f"**{step['contains']}**")
        evidence["url"] = page.url
    elif action == "wait":
        page.wait_for_timeout(int(step.get("ms", 1000)))
    elif action == "screenshot":
        image = page.screenshot(full_page=bool(step.get("full_page", True)))
        evidence["screenshot_bytes"] = len(image)
        evidence["screenshot_sha256"] = hashlib.sha256(image).hexdigest()
