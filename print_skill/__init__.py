"""print_skill: Home office printing capability for autonomous AI agents in BeerCanLabs Agent Factory.

Provides plain text, document file, and public URL printing to the home office printer,
routed through the zero-trust Gatekeeper Egress proxy.

Example usage:
    from print_skill import print_text, get_health, list_printers

    # Check printer readiness
    status = get_health()
    if status.get("ok"):
        # Send text document to default printer
        result = print_text("Morning briefing agenda items:\\n- Standup 9am\\n- Client Review 2pm")
"""

from __future__ import annotations

from typing import Any

from print_skill.client import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_COPIES,
    MAX_PAYLOAD_BYTES,
    PrintClient,
    PrintError,
)

__all__ = [
    "PrintClient",
    "PrintError",
    "print_text",
    "print_file",
    "print_url",
    "get_health",
    "list_printers",
    "list_jobs",
    "cancel_job",
    "DEFAULT_TIMEOUT_SECONDS",
    "MAX_COPIES",
    "MAX_PAYLOAD_BYTES",
    "__version__",
]

__version__ = "0.1.0"


def _default_client() -> PrintClient:
    return PrintClient()


def print_text(
    text: str,
    title: str | None = None,
    copies: int = 1,
    printer: str | None = None,
) -> dict[str, Any]:
    """Print plain text or markdown to the office printer."""
    return _default_client().print_text(text=text, title=title, copies=copies, printer=printer)


def print_file(
    data: bytes | str,
    filename: str = "document.pdf",
    title: str | None = None,
    copies: int = 1,
    printer: str | None = None,
) -> dict[str, Any]:
    """Print a local document file (raw bytes or base64) to the office printer."""
    return _default_client().print_file(data=data, filename=filename, title=title, copies=copies, printer=printer)


def print_url(
    url: str,
    title: str | None = None,
    copies: int = 1,
    printer: str | None = None,
) -> dict[str, Any]:
    """Print a document from a public URL to the office printer."""
    return _default_client().print_url(url=url, title=title, copies=copies, printer=printer)


def get_health() -> dict[str, Any]:
    """Check connectivity to the printer daemon and print queue health."""
    return _default_client().get_health()


def list_printers() -> dict[str, Any]:
    """List available CUPS printers at the home bridge."""
    return _default_client().list_printers()


def list_jobs() -> dict[str, Any]:
    """List active or pending jobs in the print queue."""
    return _default_client().list_jobs()


def cancel_job(job_id: str) -> dict[str, Any]:
    """Cancel a queued print job."""
    return _default_client().cancel_job(job_id=job_id)
