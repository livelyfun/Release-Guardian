#!/usr/bin/env python3
"""Small dependency-free CLI for the Release Guardian HTTP API.

Examples:
    python scripts/rg.py login --email you@example.com --password ...
    python scripts/rg.py monitors --workspace <workspace-id>
    python scripts/rg.py trigger <monitor-id>
    python scripts/rg.py export-runs --workspace <workspace-id> --output runs.csv

Authentication uses the token saved by ``login`` (config lives in
``~/.config/release-guardian/cli.json``) or the ``RG_TOKEN`` environment
variable. Set ``RG_API_URL`` to point at a non-local API.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_API_URL = "http://localhost:8000/api/v1"
CONFIG_PATH = Path(
    os.environ.get(
        "RG_CONFIG",
        Path.home() / ".config" / "release-guardian" / "cli.json",
    )
)


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    CONFIG_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)


def _api_url(args: argparse.Namespace) -> str:
    return (
        args.api_url
        or os.environ.get("RG_API_URL")
        or _load_config().get("api_url")
        or DEFAULT_API_URL
    ).rstrip("/")


def _token(args: argparse.Namespace) -> str | None:
    return args.token or os.environ.get("RG_TOKEN") or _load_config().get("token")


def _request(
    args: argparse.Namespace,
    method: str,
    path: str,
    body: dict | None = None,
    *,
    raw: bool = False,
) -> dict | list | str | None:
    headers = {"Accept": "application/json"}
    token = _token(args)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()

    request = urllib.request.Request(
        _api_url(args) + path, data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read().decode()
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode(errors="replace")
        try:
            error = json.loads(payload).get("error") or json.loads(payload).get("detail")
        except ValueError:
            error = payload
        print(f"API error {exc.code}: {error}", file=sys.stderr)
        raise SystemExit(1) from exc
    except urllib.error.URLError as exc:
        print(f"API unreachable: {exc.reason}", file=sys.stderr)
        raise SystemExit(1) from exc

    if raw:
        return payload
    return json.loads(payload) if payload else None


def _print(payload, as_json: bool, columns: list[str] | None = None) -> None:
    if as_json or columns is None:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    rows = payload or []
    print("\t".join(columns))
    for row in rows:
        print("\t".join("" if row.get(column) is None else str(row.get(column)) for column in columns))


def cmd_login(args: argparse.Namespace) -> None:
    body = {"email": args.email, "password": args.password}
    if args.register:
        body["name"] = args.name
        path = "/auth/register"
    else:
        path = "/auth/login"
    result = _request(args, "POST", path, body)
    config = _load_config()
    config.update(
        {
            "api_url": _api_url(args),
            "token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "email": result["user"]["email"],
        }
    )
    _save_config(config)
    print(f"Signed in as {result['user']['email']} ({result['user']['name']})")


def cmd_workspaces(args: argparse.Namespace) -> None:
    _print(
        _request(args, "GET", "/workspaces"),
        args.json,
        ["id", "name", "slug", "role"],
    )


def cmd_projects(args: argparse.Namespace) -> None:
    path = "/projects"
    if args.workspace:
        path += "?" + urllib.parse.urlencode({"workspace_id": args.workspace})
    _print(_request(args, "GET", path), args.json, ["id", "name", "workspace_id"])


def cmd_environments(args: argparse.Namespace) -> None:
    path = f"/projects/{args.project}/environments"
    _print(_request(args, "GET", path), args.json, ["id", "name", "base_url", "is_production"])


def cmd_monitors(args: argparse.Namespace) -> None:
    if args.environment:
        path = "/monitors?" + urllib.parse.urlencode({"environment_id": args.environment})
    elif args.workspace:
        path = "/monitors?" + urllib.parse.urlencode({"workspace_id": args.workspace})
    else:
        raise SystemExit("Pass --workspace or --environment")
    _print(
        _request(args, "GET", path),
        args.json,
        ["id", "name", "kind", "target_url", "enabled"],
    )


def cmd_runs(args: argparse.Namespace) -> None:
    if args.monitor:
        path = f"/monitors/{args.monitor}/runs?" + urllib.parse.urlencode(
            {"limit": args.limit}
        )
    elif args.workspace:
        path = "/runs?" + urllib.parse.urlencode(
            {"workspace_id": args.workspace, "limit": args.limit}
        )
    else:
        raise SystemExit("Pass --workspace or --monitor")
    _print(
        _request(args, "GET", path),
        args.json,
        ["id", "monitor_id", "status", "trigger", "duration_ms", "created_at"],
    )


def cmd_trigger(args: argparse.Namespace) -> None:
    result = _request(
        args,
        "POST",
        f"/monitors/{args.monitor}/runs",
        {"trigger": args.trigger_kind},
    )
    _print(result, True)


def cmd_incidents(args: argparse.Namespace) -> None:
    params = {"workspace_id": args.workspace}
    if args.status:
        params["status"] = args.status
    path = "/incidents?" + urllib.parse.urlencode(params)
    _print(
        _request(args, "GET", path),
        args.json,
        ["id", "title", "severity", "status", "opened_at"],
    )


def cmd_deployments(args: argparse.Namespace) -> None:
    path = f"/environments/{args.environment}/deployments"
    _print(
        _request(args, "GET", path),
        args.json,
        ["id", "commit_sha", "branch", "status", "created_at"],
    )


def cmd_deploy(args: argparse.Namespace) -> None:
    body = {"commit_sha": args.commit, "status": args.status}
    if args.branch:
        body["branch"] = args.branch
    if args.pr is not None:
        body["pull_request"] = args.pr
    _print(_request(args, "POST", f"/environments/{args.environment}/deployments", body), True)


def cmd_export(args: argparse.Namespace) -> None:
    if args.kind == "runs":
        path = "/runs/export.csv?" + urllib.parse.urlencode({"workspace_id": args.workspace})
        default = "runs.csv"
    else:
        path = "/incidents/export.csv?" + urllib.parse.urlencode(
            {"workspace_id": args.workspace}
        )
        default = "incidents.csv"
    output = Path(args.output or default)
    output.write_text(_request(args, "GET", path, raw=True), encoding="utf-8")
    print(f"Wrote {output}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Release Guardian CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--api-url", help="API base URL (default: RG_API_URL or localhost)")
    parser.add_argument("--token", help="API token (default: saved token or RG_TOKEN)")
    parser.add_argument("--json", action="store_true", help="Print raw JSON")
    subparsers = parser.add_subparsers(dest="command", required=True)

    login = subparsers.add_parser("login", help="Sign in and save a token")
    login.add_argument("--email", required=True)
    login.add_argument("--password", required=True)
    login.add_argument("--register", action="store_true", help="Create the account instead")
    login.add_argument("--name", default="Release Guardian user")
    login.set_defaults(func=cmd_login)

    workspaces = subparsers.add_parser("workspaces", help="List workspaces")
    workspaces.set_defaults(func=cmd_workspaces)

    projects = subparsers.add_parser("projects", help="List projects")
    projects.add_argument("--workspace")
    projects.set_defaults(func=cmd_projects)

    environments = subparsers.add_parser("environments", help="List environments")
    environments.add_argument("--project", required=True)
    environments.set_defaults(func=cmd_environments)

    monitors = subparsers.add_parser("monitors", help="List monitors")
    monitors.add_argument("--workspace")
    monitors.add_argument("--environment")
    monitors.set_defaults(func=cmd_monitors)

    runs = subparsers.add_parser("runs", help="List runs")
    runs.add_argument("--workspace")
    runs.add_argument("--monitor")
    runs.add_argument("--limit", type=int, default=50)
    runs.set_defaults(func=cmd_runs)

    trigger = subparsers.add_parser("trigger", help="Trigger a run")
    trigger.add_argument("monitor")
    trigger.add_argument("--trigger", default="manual", dest="trigger_kind")
    trigger.set_defaults(func=cmd_trigger)

    incidents = subparsers.add_parser("incidents", help="List incidents")
    incidents.add_argument("--workspace", required=True)
    incidents.add_argument("--status")
    incidents.set_defaults(func=cmd_incidents)

    deployments = subparsers.add_parser("deployments", help="List deployments")
    deployments.add_argument("--environment", required=True)
    deployments.set_defaults(func=cmd_deployments)

    deploy = subparsers.add_parser("deploy", help="Record a deployment")
    deploy.add_argument("--environment", required=True)
    deploy.add_argument("--commit", required=True)
    deploy.add_argument("--branch")
    deploy.add_argument("--pr", type=int)
    deploy.add_argument("--status", default="success")
    deploy.set_defaults(func=cmd_deploy)

    export = subparsers.add_parser("export", help="Download a CSV export")
    export.add_argument("kind", choices=["runs", "incidents"])
    export.add_argument("--workspace", required=True)
    export.add_argument("--output")
    export.set_defaults(func=cmd_export)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
