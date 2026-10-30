"""print_skill.client: Gatekeeper-egress client for the print route.

In the BeerCanLabs Agent Factory architecture:
- Agents run in network-isolated private subnets with no raw internet access (DESIGN_AUTHORITY §6.1, E1).
- Outbound network traffic is routed through the internal gatekeeper-egress (E1).
- The agent authenticates to the gatekeeper-egress using its ephemeral FACTORY_RUN_TOKEN.
- The gatekeeper-egress validates that the agent's policy permits the 'print' route, strips the run token,
  injects the held credential (PRINT_API_TOKEN) into the request, and forwards it to the upstream print bridge (S1, K3).
- Zero provider secrets are held by the agent or committed in this repository.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Mapping

log = logging.getLogger("print_skill")

DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_COPIES = 5
MAX_PAYLOAD_BYTES = 25 * 1024 * 1024  # 25 MB cap

_ORIGINAL_URLOPEN = urllib.request.urlopen
_DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _urlopen(req: urllib.request.Request, timeout: float):
    if urllib.request.urlopen is not _ORIGINAL_URLOPEN:
        return urllib.request.urlopen(req, timeout=timeout)
    return _DIRECT.open(req, timeout=timeout)


class PrintError(Exception):
    """Raised when a print operation fails or is refused by the bridge."""

    def __init__(self, message: str, error_code: str = "PrintError", detail: Any = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.detail = detail

    def to_dict(self) -> dict[str, Any]:
        res = {"ok": False, "error": self.error_code, "message": self.message}
        if self.detail is not None:
            res["detail"] = self.detail
        return res


class PrintClient:
    """HTTP client communicating with the print bridge via Gatekeeper Egress."""

    def __init__(
        self,
        base_url: str | None = None,
        run_token: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        env: Mapping[str, str] | None = None,
    ):
        environ = env if env is not None else os.environ
        # 1. Base URL: Route 'print' injected by the factory shim or explicitly configured
        configured_url = base_url or environ.get("PRINT_BASE_URL")
        if not configured_url:
            egress_host = environ.get("FACTORY_GATEKEEPER_EGRESS_URL") or environ.get("GATEKEEPER_EGRESS_URL")
            if egress_host:
                configured_url = f"{egress_host.rstrip('/')}/print"
            else:
                # Default loopback for local development or testing
                configured_url = "http://127.0.0.1:3001/print"

        self.base_url = configured_url.rstrip("/")
        # 2. Ephemeral Run Token: Issued to the container by the Factory Control Plane
        self.run_token = run_token or environ.get("FACTORY_RUN_TOKEN", "")
        self.timeout = timeout

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        clean_path = ("/" + path.lstrip("/")) if path else ""
        url = f"{self.base_url}{clean_path}"

        headers = {
            "User-Agent": "BeerCanLabs-AgentFactory-SkillPrint/0.1.0",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.run_token:
            headers["Authorization"] = f"Bearer {self.run_token}"

        data_bytes = None
        if payload is not None:
            data_bytes = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method.upper())

        try:
            with _urlopen(req, timeout=self.timeout) as resp:
                resp_bytes = resp.read()
                if not resp_bytes:
                    return {"ok": True, "status": resp.status}
                return json.loads(resp_bytes.decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(err_body)
                if isinstance(parsed, dict) and "error" in parsed:
                    return {"ok": False, "status": e.code, **parsed}
            except Exception:
                pass
            return {
                "ok": False,
                "status": e.code,
                "error": "HttpError",
                "message": f"Print request failed with HTTP {e.code}: {e.reason}",
                "detail": err_body,
            }
        except urllib.error.URLError as e:
            return {
                "ok": False,
                "error": "NetworkError",
                "message": f"Unable to reach Gatekeeper print route: {e.reason}",
            }
        except TimeoutError:
            return {
                "ok": False,
                "error": "TimeoutError",
                "message": f"Print request timed out after {self.timeout}s",
            }
        except json.JSONDecodeError as e:
            return {
                "ok": False,
                "error": "InvalidResponse",
                "message": f"Malformed JSON from print service: {e}",
            }
        except Exception as e:
            return {
                "ok": False,
                "error": "ClientError",
                "message": f"Unexpected error during print request: {e}",
            }

    def print_text(
        self,
        text: str,
        title: str | None = None,
        copies: int = 1,
        printer: str | None = None,
    ) -> dict[str, Any]:
        """Print a plain text or markdown document."""
        if not text or not text.strip():
            return {"ok": False, "error": "EmptyDocument", "message": "Refusing to print empty text."}

        copies = max(1, min(int(copies), MAX_COPIES))
        payload = {
            "kind": "text",
            "text": text,
            "title": title or "Factory Document",
            "copies": copies,
        }
        if printer:
            payload["printer"] = printer

        return self._request("POST", "/jobs", payload)

    def print_file(
        self,
        data: bytes | str,
        filename: str = "document.pdf",
        title: str | None = None,
        copies: int = 1,
        printer: str | None = None,
    ) -> dict[str, Any]:
        """Print raw binary bytes or a base64 encoded document (PDF, PNG, etc.)."""
        if isinstance(data, str):
            raw_bytes = base64.b64decode(data)
        else:
            raw_bytes = data

        if not raw_bytes:
            return {"ok": False, "error": "EmptyDocument", "message": "Refusing to print empty file."}

        if len(raw_bytes) > MAX_PAYLOAD_BYTES:
            return {
                "ok": False,
                "error": "TooLarge",
                "message": f"Document exceeds size limit of {MAX_PAYLOAD_BYTES // (1024 * 1024)}MB.",
            }

        copies = max(1, min(int(copies), MAX_COPIES))
        payload = {
            "kind": "file",
            "filename": filename,
            "payload": base64.b64encode(raw_bytes).decode("ascii"),
            "title": title or filename,
            "copies": copies,
        }
        if printer:
            payload["printer"] = printer

        return self._request("POST", "/jobs", payload)

    def print_url(
        self,
        url: str,
        title: str | None = None,
        copies: int = 1,
        printer: str | None = None,
    ) -> dict[str, Any]:
        """Print a public URL document (PDF, webpage, image)."""
        if not url or not url.strip():
            return {"ok": False, "error": "InvalidUrl", "message": "A document URL is required."}

        copies = max(1, min(int(copies), MAX_COPIES))
        payload = {
            "kind": "url",
            "url": url.strip(),
            "title": title or "URL Document",
            "copies": copies,
        }
        if printer:
            payload["printer"] = printer

        return self._request("POST", "/jobs", payload)

    def get_health(self) -> dict[str, Any]:
        """Check printer connectivity, bridge daemon heartbeat, and queue status."""
        return self._request("GET", "/health")

    def list_printers(self) -> dict[str, Any]:
        """List all discovered local CUPS printers and the default destination."""
        return self._request("GET", "/printers")

    def list_jobs(self) -> dict[str, Any]:
        """List active or pending jobs in the queue."""
        return self._request("GET", "/jobs")

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        """Cancel a queued print job by id."""
        if not job_id:
            return {"ok": False, "error": "InvalidJobId", "message": "Job ID is required to cancel."}
        return self._request("POST", "/cancel", {"job_id": job_id})
