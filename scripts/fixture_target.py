#!/usr/bin/env python3
"""Local fixture target used by load and smoke tests.

Serves a small HTML page plus latency/failure endpoints so HTTP, browser, and
Lighthouse checks can run without external network access.

Usage:
    python scripts/fixture_target.py --port 8099
"""

from __future__ import annotations

import argparse
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PAGE = """<!doctype html>
<html lang="en">
  <head><meta charset="utf-8"><title>Release Guardian fixture</title></head>
  <body>
    <h1>Release Guardian fixture target</h1>
    <p id="status">ready</p>
    <a id="next" href="/health">health</a>
  </body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "ReleaseGuardianFixture/1.0"

    def _send(self, status: int, body: str, content_type: str = "text/html") -> None:
        payload = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self._send(200, PAGE)
            return
        if parsed.path == "/health":
            self._send(200, '{"status":"ok"}', "application/json")
            return
        if parsed.path == "/slow":
            delay_ms = int(parse_qs(parsed.query).get("ms", ["200"])[0])
            time.sleep(min(delay_ms, 5000) / 1000)
            self._send(200, "slow response")
            return
        if parsed.path == "/fail":
            self._send(500, "intentional failure")
            return
        self._send(404, "not found")

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        # Keep fixture output quiet; load tests print their own summary.
        return


def serve(port: int, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), Handler)
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Release Guardian fixture target")
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    server = serve(args.port, args.host)
    print(f"fixture target listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
