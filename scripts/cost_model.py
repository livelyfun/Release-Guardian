#!/usr/bin/env python3
"""Transparent cost model for Release Guardian.

All prices are inputs.  Defaults are illustrative placeholders, not quotes --
verify current provider pricing and regions before making commitments (see
docs/master-plan/release-guardian/13-COST-AND-CAPACITY-MODEL.md).

Example:
    python scripts/cost_model.py --checks-per-month 200000 --browser-share 0.2
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_model(args) -> dict:
    browser_checks = args.checks_per_month * args.browser_share
    lighthouse_checks = args.checks_per_month * args.lighthouse_share
    http_checks = max(0.0, args.checks_per_month - browser_checks - lighthouse_checks)

    worker_seconds = (
        http_checks * args.http_seconds_per_check
        + browser_checks * args.browser_seconds_per_check
        + lighthouse_checks * args.lighthouse_seconds_per_check
    )
    worker_hours = worker_seconds / 3600
    worker_cost = worker_hours * args.worker_hour_usd

    # Steady-state artifact storage for the retention window.
    retained_months = args.retention_days / 30
    artifact_gb = (
        args.checks_per_month * retained_months * args.artifact_kb_per_check
    ) / (1024 * 1024)
    storage_cost = artifact_gb * args.storage_gb_month_usd

    egress_cost = args.egress_gb_per_month * args.egress_gb_usd
    notification_cost = args.notifications_per_month * args.notification_usd
    ai_cost = args.ai_calls_per_month * args.ai_call_usd

    components = {
        "worker_compute": round(worker_cost, 2),
        "artifact_storage": round(storage_cost, 2),
        "network_egress": round(egress_cost, 2),
        "notifications": round(notification_cost, 2),
        "database": round(args.database_month_usd, 2),
        "redis": round(args.redis_month_usd, 2),
        "fixed_hosting": round(args.fixed_hosting_month_usd, 2),
        "ai_tokens": round(ai_cost, 2),
    }
    total = round(sum(components.values()), 2)

    return {
        "inputs": {
            "checks_per_month": args.checks_per_month,
            "browser_share": args.browser_share,
            "lighthouse_share": args.lighthouse_share,
            "artifact_kb_per_check": args.artifact_kb_per_check,
            "retention_days": args.retention_days,
            "worker_hour_usd": args.worker_hour_usd,
            "storage_gb_month_usd": args.storage_gb_month_usd,
            "egress_gb_usd": args.egress_gb_usd,
        },
        "volume": {
            "http_checks": round(http_checks),
            "browser_checks": round(browser_checks),
            "lighthouse_checks": round(lighthouse_checks),
            "worker_hours": round(worker_hours, 1),
            "artifact_gb_retained": round(artifact_gb, 1),
        },
        "components_usd": components,
        "total_month_usd": total,
        "cost_per_check_usd": round(total / args.checks_per_month, 6)
        if args.checks_per_month
        else 0,
        "caveat": "Prices are inputs, not quotes. Validate with the provider before commitments.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Release Guardian cost model")
    parser.add_argument("--checks-per-month", type=int, default=100_000)
    parser.add_argument("--browser-share", type=float, default=0.20)
    parser.add_argument("--lighthouse-share", type=float, default=0.05)
    parser.add_argument("--http-seconds-per-check", type=float, default=1.0)
    parser.add_argument("--browser-seconds-per-check", type=float, default=45.0)
    parser.add_argument("--lighthouse-seconds-per-check", type=float, default=60.0)
    parser.add_argument("--artifact-kb-per-check", type=float, default=250.0)
    parser.add_argument("--retention-days", type=int, default=30)
    parser.add_argument("--worker-hour-usd", type=float, default=0.05)
    parser.add_argument("--storage-gb-month-usd", type=float, default=0.023)
    parser.add_argument("--egress-gb-per-month", type=float, default=50.0)
    parser.add_argument("--egress-gb-usd", type=float, default=0.09)
    parser.add_argument("--notifications-per-month", type=int, default=5_000)
    parser.add_argument("--notification-usd", type=float, default=0.001)
    parser.add_argument("--database-month-usd", type=float, default=100.0)
    parser.add_argument("--redis-month-usd", type=float, default=30.0)
    parser.add_argument("--fixed-hosting-month-usd", type=float, default=150.0)
    parser.add_argument("--ai-calls-per-month", type=int, default=0)
    parser.add_argument("--ai-call-usd", type=float, default=0.002)
    parser.add_argument("--output", default=None, help="Write the model to a JSON file")
    args = parser.parse_args()

    model = build_model(args)
    text = json.dumps(model, indent=2)
    print(text)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
