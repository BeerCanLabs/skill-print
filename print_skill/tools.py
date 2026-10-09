"""print_skill.tools: Tool function definitions for LLM agent integration (Donna, Higgins, etc.)."""

from __future__ import annotations

import json
from typing import Any

from print_skill.client import PrintClient


def tool_print_text(
    text: str,
    title: str | None = None,
    copies: int = 1,
    printer: str | None = None,
) -> str:
    """Print text, notes, meeting agendas, or checklists to the home office printer.

    Args:
        text: The text body to print. Markdown syntax will print literally; simple formatting is recommended.
        title: Optional document title for the print job header.
        copies: Number of physical copies (capped between 1 and 5).
        printer: Specific destination printer name (defaults to system default).

    Returns:
        JSON string representing the print job outcome.
    """
    client = PrintClient()
    res = client.print_text(text=text, title=title, copies=copies, printer=printer)
    return json.dumps(res, indent=2)


def tool_print_url(
    url: str,
    title: str | None = None,
    copies: int = 1,
    printer: str | None = None,
) -> str:
    """Print a document from a publicly accessible URL (e.g. PDF statement, web invoice).

    Args:
        url: Public HTTP/HTTPS URL of the document to fetch and print.
        title: Optional document title.
        copies: Number of copies (1-5).
        printer: Specific destination printer name.

    Returns:
        JSON string representing the print job outcome.
    """
    client = PrintClient()
    res = client.print_url(url=url, title=title, copies=copies, printer=printer)
    return json.dumps(res, indent=2)


def tool_check_printer_health() -> str:
    """Check whether the home office printer and daemon bridge are awake and ready for jobs.

    Returns:
        JSON string with printer availability and queue status.
    """
    client = PrintClient()
    res = client.get_health()
    return json.dumps(res, indent=2)


def tool_list_printers() -> str:
    """List all available office printers and the default printer destination.

    Returns:
        JSON string listing printer names and states.
    """
    client = PrintClient()
    res = client.list_printers()
    return json.dumps(res, indent=2)


def tool_cancel_job(job_id: str) -> str:
    """Cancel a pending or stuck print job.

    Args:
        job_id: The job identifier returned when the print job was queued.

    Returns:
        JSON string confirming cancellation.
    """
    client = PrintClient()
    res = client.cancel_job(job_id=job_id)
    return json.dumps(res, indent=2)
