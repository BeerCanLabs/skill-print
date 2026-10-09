"""print_skill.cli: CLI interface for the print skill."""

from __future__ import annotations

import argparse
import json
import sys

from print_skill.client import PrintClient


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BeerCanLabs Agent Factory Print CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # text
    p_text = subparsers.add_parser("text", help="Print plain text")
    p_text.add_argument("--message", "-m", help="Text to print")
    p_text.add_argument("--stdin", action="store_true", help="Read text from standard input")
    p_text.add_argument("--title", "-t", default=None, help="Document title")
    p_text.add_argument("--copies", "-c", type=int, default=1, help="Number of copies")
    p_text.add_argument("--printer", "-p", default=None, help="Target printer name")

    # url
    p_url = subparsers.add_parser("url", help="Print document from public URL")
    p_url.add_argument("url", help="Public URL to document")
    p_url.add_argument("--title", "-t", default=None, help="Document title")
    p_url.add_argument("--copies", "-c", type=int, default=1, help="Number of copies")
    p_url.add_argument("--printer", "-p", default=None, help="Target printer name")

    # file
    p_file = subparsers.add_parser("file", help="Print local file")
    p_file.add_argument("path", help="Path to local file")
    p_file.add_argument("--title", "-t", default=None, help="Document title")
    p_file.add_argument("--copies", "-c", type=int, default=1, help="Number of copies")
    p_file.add_argument("--printer", "-p", default=None, help="Target printer name")

    # health
    subparsers.add_parser("health", help="Check printer health")

    # printers
    subparsers.add_parser("printers", help="List available printers")

    # jobs
    subparsers.add_parser("jobs", help="List active jobs")

    # cancel
    p_cancel = subparsers.add_parser("cancel", help="Cancel a print job")
    p_cancel.add_argument("job_id", help="Job ID to cancel")

    args = parser.parse_args(argv)
    client = PrintClient()

    if args.command == "text":
        content = sys.stdin.read() if args.stdin else (args.message or "")
        res = client.print_text(text=content, title=args.title, copies=args.copies, printer=args.printer)
    elif args.command == "url":
        res = client.print_url(url=args.url, title=args.title, copies=args.copies, printer=args.printer)
    elif args.command == "file":
        with open(args.path, "rb") as f:
            raw = f.read()
        res = client.print_file(data=raw, filename=args.path, title=args.title, copies=args.copies, printer=args.printer)
    elif args.command == "health":
        res = client.get_health()
    elif args.command == "printers":
        res = client.list_printers()
    elif args.command == "jobs":
        res = client.list_jobs()
    elif args.command == "cancel":
        res = client.cancel_job(job_id=args.job_id)
    else:
        res = {"ok": False, "error": "UnknownCommand", "message": f"Unknown command: {args.command}"}

    print(json.dumps(res, indent=2))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
