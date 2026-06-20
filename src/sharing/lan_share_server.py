"""PIN-protected LAN sharing server for formula history."""

from __future__ import annotations

import json
import secrets
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from sharing.history_package import dumps_package, parse_history_package

PackageProvider = Callable[[], dict[str, Any]]
PackageImporter = Callable[[dict[str, Any]], tuple[int, int]]
RecognizeProvider = Callable[[bytes, str], dict[str, Any]]


def get_local_ipv4s() -> list[str]:
    """Return likely LAN IPv4 addresses for display in the pairing dialog."""
    addresses: set[str] = set()
    try:
        host_name = socket.gethostname()
        for info in socket.getaddrinfo(host_name, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                addresses.add(ip)
    except Exception:
        pass

    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        ip = probe.getsockname()[0]
        if ip and not ip.startswith("127."):
            addresses.add(ip)
        probe.close()
    except Exception:
        pass

    return sorted(addresses)


class LanShareServer:
    """Small HTTP server used while the desktop share dialog is open."""

    def __init__(
        self,
        package_provider: PackageProvider,
        package_importer: PackageImporter,
        *,
        recognize_provider: RecognizeProvider | None = None,
        host: str = "0.0.0.0",
        port: int = 0,
    ) -> None:
        self.pin = f"{secrets.randbelow(1_000_000):06d}"
        self._package_provider = package_provider
        self._package_importer = package_importer
        self._recognize_provider = recognize_provider
        self._server = ThreadingHTTPServer((host, port), self._make_handler())
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def port(self) -> int:
        return int(self._server.server_address[1])

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    def display_urls(self) -> list[str]:
        ips = get_local_ipv4s() or ["127.0.0.1"]
        return [f"http://{ip}:{self.port}" for ip in ips]

    def _make_handler(self) -> type[BaseHTTPRequestHandler]:
        outer = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "LaTeXSnipperLanShare/1.0"

            def log_message(self, _format: str, *_args: Any) -> None:
                return

            def do_OPTIONS(self) -> None:
                self._send_empty(204)

            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                if parsed.path == "/api/v1/info":
                    body = {
                        "ok": True,
                        "app": "LaTeXSnipper",
                        "schema": "latexsnipper.share.history.v1",
                        "requiresPin": True,
                    }
                    self._send_json(200, body)
                    return
                if parsed.path == "/api/v1/history":
                    if not self._pin_matches(parsed.query):
                        self._send_json(403, {"ok": False, "error": "invalid_pin"})
                        return
                    self._send_bytes(200, dumps_package(outer._package_provider()))
                    return
                self._send_json(404, {"ok": False, "error": "not_found"})

            def do_POST(self) -> None:
                parsed = urlparse(self.path)
                if parsed.path == "/api/v1/history/import":
                    if not self._pin_matches(parsed.query):
                        self._send_json(403, {"ok": False, "error": "invalid_pin"})
                        return
                    try:
                        length = int(self.headers.get("Content-Length", "0"))
                        if length <= 0 or length > 8 * 1024 * 1024:
                            raise ValueError("invalid request size")
                        package = parse_history_package(self.rfile.read(length))
                        added, updated = outer._package_importer(package)
                        self._send_json(200, {"ok": True, "added": added, "updated": updated})
                    except Exception as exc:
                        self._send_json(400, {"ok": False, "error": str(exc)})
                    return
                if parsed.path == "/api/v1/recognize":
                    if not self._pin_matches(parsed.query):
                        self._send_json(403, {"ok": False, "error": "invalid_pin"})
                        return
                    if outer._recognize_provider is None:
                        self._send_json(501, {"ok": False, "error": "recognition not available"})
                        return
                    try:
                        length = int(self.headers.get("Content-Length", "0"))
                        if length <= 0 or length > 10 * 1024 * 1024:
                            raise ValueError("invalid request size")
                        body = json.loads(self.rfile.read(length))
                        image_b64 = body.get("image", "")
                        mode = body.get("mode", "formula")
                        if not image_b64:
                            raise ValueError("missing image field")
                        image_bytes = __import__("base64").b64decode(image_b64)
                        result = outer._recognize_provider(image_bytes, mode)
                        self._send_json(200, {"ok": True, **result})
                    except Exception as exc:
                        self._send_json(400, {"ok": False, "error": str(exc)})
                    return
                self._send_json(404, {"ok": False, "error": "not_found"})

            def _pin_matches(self, query: str) -> bool:
                qs = parse_qs(query)
                supplied = qs.get("pin", [""])[0] or self.headers.get("X-LaTeXSnipper-Pin", "")
                return secrets.compare_digest(str(supplied), outer.pin)

            def _send_empty(self, status: int) -> None:
                self.send_response(status)
                self._send_common_headers()
                self.end_headers()

            def _send_json(self, status: int, body: dict[str, Any]) -> None:
                data = json.dumps(body, ensure_ascii=False).encode("utf-8")
                self._send_bytes(status, data, "application/json; charset=utf-8")

            def _send_bytes(
                self,
                status: int,
                body: bytes,
                content_type: str = "application/json; charset=utf-8",
            ) -> None:
                self.send_response(status)
                self._send_common_headers()
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _send_common_headers(self) -> None:
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, X-LaTeXSnipper-Pin")
                self.send_header("Cache-Control", "no-store")

        return Handler
