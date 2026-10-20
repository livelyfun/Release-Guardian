from types import SimpleNamespace

import app.services.checks as checks_module
from app.services.browser import perform_browser_check
from app.services.outcomes import CheckOutcome, StepOutcome


def _monitor(kind="browser", config=None):
    return SimpleNamespace(
        kind=kind,
        config=config if config is not None else {},
        target_url="https://example.com",
    )


def test_perform_check_routes_browser_monitors(monkeypatch):
    calls = []
    monkeypatch.setattr(
        checks_module,
        "perform_browser_check",
        lambda monitor, run_id=None: calls.append("browser")
        or CheckOutcome(status="passed", duration_ms=1, steps=[], summary={}),
    )
    monkeypatch.setattr(
        checks_module,
        "perform_http_check",
        lambda monitor, run_id=None: calls.append("http")
        or CheckOutcome(status="passed", duration_ms=1, steps=[], summary={}),
    )

    checks_module.perform_check(_monitor("browser", {"steps": [{"action": "goto"}]}))
    checks_module.perform_check(_monitor("http"))

    assert calls == ["browser", "http"]


def test_browser_check_rejects_missing_steps():
    outcome = perform_browser_check(_monitor("browser", {}))
    assert outcome.status == "failed"
    assert "No browser steps" in outcome.steps[0].error


def test_browser_check_rejects_unsupported_action():
    outcome = perform_browser_check(
        _monitor("browser", {"steps": [{"action": "download"}]})
    )
    assert outcome.status == "failed"
    assert "Unsupported action" in outcome.steps[0].error


def test_browser_check_rejects_too_many_steps():
    steps = [{"action": "wait", "ms": 1} for _ in range(51)]
    outcome = perform_browser_check(_monitor("browser", {"steps": steps}))
    assert outcome.status == "failed"
    assert "Too many steps" in outcome.steps[0].error


def test_step_outcome_evidence_defaults_are_independent():
    first = StepOutcome(name="a", status="passed", duration_ms=1)
    second = StepOutcome(name="b", status="passed", duration_ms=1)
    first.evidence["x"] = 1
    assert second.evidence == {}
