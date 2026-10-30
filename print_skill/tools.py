"""print_skill.tools: Tool function definitions and shared-runtime tools() export."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from print_skill.client import PrintClient

STAGING_DIR = Path(os.environ.get("ATTACHMENT_STAGING_DIR", "/tmp/attachments"))

TOOL_NAMES = (
    "print_text",
    "print_file_path",
    "print_url",
    "check_printer_health",
    "list_printers",
    "list_print_jobs",
    "cancel_print_job",
)

_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "print_text",
            "description": "Print plain text, notes, meeting agendas, or checklists to the home office printer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Plain text body to print."},
                    "title": {"type": "string", "description": "Optional document title."},
                    "copies": {"type": "integer", "description": "Copies to print (1-5, default 1)."},
                    "printer": {"type": "string", "description": "Destination printer name (optional)."},
                },
                "required": ["text"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "print_file_path",
            "description": "Print a PDF, PNG, or document file previously staged in /tmp/attachments.",
            "parameters": {
                "type": "object",
                "properties": {
                    "local_path": {"type": "string", "description": "Path inside /tmp/attachments."},
                    "title": {"type": "string", "description": "Optional print job title."},
                    "copies": {"type": "integer", "description": "Copies to print (1-5, default 1)."},
                    "printer": {"type": "string", "description": "Destination printer name (optional)."},
                },
                "required": ["local_path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "print_url",
            "description": "Print a document from a publicly accessible URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Public document URL to print."},
                    "title": {"type": "string", "description": "Optional print job title."},
                    "copies": {"type": "integer", "description": "Copies to print (1-5, default 1)."},
                    "printer": {"type": "string", "description": "Destination printer name (optional)."},
                },
                "required": ["url"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_printer_health",
            "description": "Check whether the home office printer and bridge daemon are online and ready.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_printers",
            "description": "List available CUPS printers and the default printer destination.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_print_jobs",
            "description": "List active or pending jobs in the print queue.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_print_job",
            "description": "Cancel a queued print job by job ID.",
            "parameters": {
                "type": "object",
                "properties": {"job_id": {"type": "string", "description": "Queued job identifier."}},
                "required": ["job_id"],
                "additionalProperties": False,
            },
        },
    },
]


def tool_definitions() -> list[dict[str, Any]]:
    return copy.deepcopy(_TOOLS)


def handle_tool_call(name: str, args: dict[str, Any]) -> dict[str, Any]:
    client = PrintClient()
    if name == "print_text":
        return client.print_text(
            text=str(args.get("text") or ""),
            title=args.get("title"),
            copies=int(args.get("copies") or 1),
            printer=args.get("printer"),
        )
    if name == "print_file_path":
        staging_root = Path(os.environ.get("ATTACHMENT_STAGING_DIR", str(STAGING_DIR))).resolve()
        candidate = Path(str(args.get("local_path") or "")).resolve()
        if candidate.parent != staging_root:
            return {"ok": False, "error": "InvalidPath", "message": "local_path must be inside /tmp/attachments."}
        if not candidate.is_file():
            return {"ok": False, "error": "NotFound", "message": f"Staged file not found: {candidate}"}
        return client.print_file(
            data=candidate.read_bytes(),
            filename=candidate.name,
            title=args.get("title") or candidate.name,
            copies=int(args.get("copies") or 1),
            printer=args.get("printer"),
        )
    if name == "print_url":
        return client.print_url(
            url=str(args.get("url") or ""),
            title=args.get("title"),
            copies=int(args.get("copies") or 1),
            printer=args.get("printer"),
        )
    if name == "check_printer_health":
        return client.get_health()
    if name == "list_printers":
        return client.list_printers()
    if name == "list_print_jobs":
        return client.list_jobs()
    if name == "cancel_print_job":
        return client.cancel_job(job_id=str(args.get("job_id") or ""))
    return {"ok": False, "error": "UnknownTool", "message": f"Unknown tool: {name}"}


def _make_handler(name: str):
    def handler(arguments: dict[str, Any] | None = None, context: dict[str, Any] | None = None) -> str:
        ctx = context or {}
        args = arguments or {}
        if ctx.get("dryRun") is True and name in ("print_text", "print_file_path", "print_url", "cancel_print_job"):
            return json.dumps({"ok": True, "dryRun": True, "tool": name})
        res = handle_tool_call(name, args)
        if ctx.get("smoke") is True and not res.get("ok"):
            return f"error: {res.get('error')}: {res.get('message') or res}"
        return json.dumps(res)

    return handler


def tools() -> list[dict[str, Any]]:
    out = []
    for tool in tool_definitions():
        fn = tool["function"]
        out.append({
            "name": fn["name"],
            "description": fn["description"],
            "parameters": fn["parameters"],
            "handler": _make_handler(fn["name"]),
        })
    return out


# Legacy helper wrappers kept for backwards compatibility
def tool_print_text(text: str, title: str | None = None, copies: int = 1, printer: str | None = None) -> str:
    return json.dumps(PrintClient().print_text(text=text, title=title, copies=copies, printer=printer), indent=2)


def tool_print_url(url: str, title: str | None = None, copies: int = 1, printer: str | None = None) -> str:
    return json.dumps(PrintClient().print_url(url=url, title=title, copies=copies, printer=printer), indent=2)


def tool_check_printer_health() -> str:
    return json.dumps(PrintClient().get_health(), indent=2)


def tool_list_printers() -> str:
    return json.dumps(PrintClient().list_printers(), indent=2)


def tool_cancel_job(job_id: str) -> str:
    return json.dumps(PrintClient().cancel_job(job_id=job_id), indent=2)
