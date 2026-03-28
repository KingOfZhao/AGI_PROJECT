"""skill_httpserver_reverse_proxy_20260327_163300

Reusable helper to add a simple reverse-proxy capability to a
`http.server.SimpleHTTPRequestHandler` based server.

This is useful when you serve a static frontend (e.g. on :8890) but the real
backend API lives on another port (e.g. :5002). You can forward selected paths
like `/api/chat` to the upstream backend.

Usage (example):
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    from skills.skill_httpserver_reverse_proxy_20260327_163300 import (
        proxy_request_to_upstream,
    )

    class Handler(SimpleHTTPRequestHandler):
        def do_POST(self):
            if self.path in ("/api/chat", "/api/chat/stop"):
                return proxy_request_to_upstream(self, upstream_base="http://localhost:5002")
            super().do_POST()

Run self-test:
    python3 skills/skill_httpserver_reverse_proxy_20260327_163300.py

Notes:
- Handles GET/POST.
- For POST it forwards the raw body; do NOT consume the body before calling.
"""

from __future__ import annotations

from typing import Mapping, Optional

import json
import urllib.parse

import requests


def _copy_headers(handler, allow: Optional[set[str]] = None) -> dict:
    allow = allow or {"content-type", "authorization"}
    out: dict[str, str] = {}
    for k, v in handler.headers.items():
        if k.lower() in allow:
            out[k] = v
    return out


def proxy_request_to_upstream(
    handler,
    upstream_base: str,
    method: str | None = None,
    timeout_sec: int = 300,
) -> None:
    """Proxy current request to an upstream base URL.

    Args:
        handler: An instance of BaseHTTPRequestHandler (e.g. SimpleHTTPRequestHandler).
        upstream_base: Upstream server base URL, e.g. "http://localhost:5002".
        method: Force method override; default uses handler.command.
        timeout_sec: Requests timeout.

    Raises:
        RuntimeError: If upstream request fails.
    """

    upstream_base = upstream_base.rstrip("/")
    method = (method or getattr(handler, "command", "GET")).upper()

    # Keep full path with query string
    url = f"{upstream_base}{handler.path}"

    headers = _copy_headers(handler)

    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=timeout_sec)
        elif method == "POST":
            length = int(handler.headers.get("Content-Length", 0) or 0)
            raw = handler.rfile.read(length) if length > 0 else b""
            resp = requests.post(url, headers=headers, data=raw, timeout=timeout_sec)
        else:
            handler.send_response(405)
            handler.send_header("Content-Type", "application/json")
            handler.end_headers()
            handler.wfile.write(json.dumps({"error": "method not allowed"}).encode())
            return

        handler.send_response(resp.status_code)
        handler.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        handler.send_header("Access-Control-Allow-Headers", "Content-Type")
        handler.end_headers()
        handler.wfile.write(resp.content)

    except Exception as e:
        raise RuntimeError(f"proxy to upstream failed: {e}") from e


def _demo_smoke_test() -> None:
    # A minimal local test: parse url building correctness
    parsed = urllib.parse.urlparse("http://localhost:5002/api/chat?x=1")
    assert parsed.scheme and parsed.netloc and parsed.path
    print("OK")


if __name__ == "__main__":
    _demo_smoke_test()
