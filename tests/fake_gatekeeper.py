"""tests.fake_gatekeeper: Lightweight local HTTP server simulating Gatekeeper Egress print route."""

from __future__ import annotations

import http.server
import json
import socket
import threading
from typing import Any

TEST_RUN_TOKEN = "".join(["test-", "run-", "token-", "456"])


class FakeGatekeeperHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass  # Quiet during tests

    @property
    def server_instance(self) -> FakeGatekeeper:
        return self.server  # type: ignore

    def do_GET(self) -> None:
        body = self.server_instance.record("GET", self.path, self.headers)
        if self.path.endswith("/health"):
            self._send_json(200, {
                "ok": True,
                "house_awake": True,
                "last_checkin_seconds_ago": 5,
                "printers": [{"name": "HP_Color_LaserJet_Pro_MFP_3301", "state": "idle"}],
                "default_printer": "HP_Color_LaserJet_Pro_MFP_3301",
                "pending": [],
            })
        elif self.path.endswith("/printers"):
            self._send_json(200, {
                "ok": True,
                "printers": [
                    {"name": "HP_Color_LaserJet_Pro_MFP_3301", "state": "idle"},
                    {"name": "Office_Brother_HL_L2350DW", "state": "idle"},
                ],
                "default": "HP_Color_LaserJet_Pro_MFP_3301",
            })
        elif self.path.endswith("/jobs"):
            self._send_json(200, {
                "ok": True,
                "pending": self.server_instance.jobs,
            })
        else:
            self._send_json(404, {"ok": False, "error": "NotFound", "message": "Unknown path"})

    def do_POST(self) -> None:
        content_len = int(self.headers.get("Content-Length", "0"))
        req_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else ""
        parsed_body = json.loads(req_body) if req_body else {}

        self.server_instance.record("POST", self.path, self.headers, parsed_body)

        if self.path.endswith("/jobs"):
            job_id = f"job-{len(self.server_instance.jobs) + 1:04d}"
            job_record = {
                "job_id": job_id,
                "kind": parsed_body.get("kind"),
                "title": parsed_body.get("title"),
                "copies": parsed_body.get("copies", 1),
                "printer": parsed_body.get("printer", "HP_Color_LaserJet_Pro_MFP_3301"),
                "status": "queued",
            }
            self.server_instance.jobs.append(job_record)
            self._send_json(200, {
                "ok": True,
                "confirmed": True,
                "printed": True,
                "job_id": job_id,
                "cups_job": "1234",
            })
        elif self.path.endswith("/cancel"):
            target_id = parsed_body.get("job_id")
            self.server_instance.jobs = [j for j in self.server_instance.jobs if j["job_id"] != target_id]
            self._send_json(200, {"ok": True, "cancelled": target_id})
        else:
            self._send_json(404, {"ok": False, "error": "NotFound", "message": "Unknown path"})

    def _send_json(self, status: int, data: dict[str, Any]) -> None:
        raw = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class FakeGatekeeper(http.server.HTTPServer):
    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), FakeGatekeeperHandler)
        self.requests: list[dict[str, Any]] = []
        self.jobs: list[dict[str, Any]] = []
        self._thread = threading.Thread(target=self.serve_forever, daemon=True)
        self._thread.start()

    def record(self, method: str, path: str, headers: Any, body: Any = None) -> None:
        self.requests.append({
            "method": method,
            "path": path,
            "auth": headers.get("Authorization"),
            "body": body,
        })

    @property
    def base_url(self) -> str:
        host, port = self.server_address
        return f"http://{host}:{port}/print"

    def close(self) -> None:
        self.shutdown()
        self.server_close()
