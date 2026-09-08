"""Command-line interface for Academic Research Tools."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import Any

from . import __version__
from .mcp_server import main as run_mcp
from .service import ResearchService
from .status import provider_status


def _json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _sources(value: str | None) -> list[str] | None:
    if value is None:
        return None
    sources = [item.strip() for item in value.split(",") if item.strip()]
    if not sources:
        raise argparse.ArgumentTypeError("sources must contain at least one provider")
    return sources


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="academic-research",
        description="Search scholarly sources through Python, CLI, or MCP.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser(
        "status", help="Show provider availability without revealing credentials"
    )
    status_parser.add_argument("--json", action="store_true", dest="as_json")

    search_parser = subparsers.add_parser(
        "search", help="Search one or more configured scholarly providers"
    )
    search_parser.add_argument("query")
    search_parser.add_argument(
        "--sources",
        help="Comma-separated providers; default uses all available providers",
    )
    search_parser.add_argument("--limit", type=int, default=10, dest="limit_per_source")
    search_parser.add_argument("--year", help="YYYY or YYYY-YYYY")

    subparsers.add_parser("serve", help="Run the MCP server over stdio")
    return parser


def _print_status(as_json: bool) -> None:
    statuses = provider_status()
    if as_json:
        print(_json(statuses))
        return
    print("Academic Research Providers")
    print()
    for name, status in statuses.items():
        marker = "✓" if status["available"] else "○"
        auth = status.get("authentication")
        detail = str(auth).replace("_", " ")
        if status.get("reason"):
            detail = str(status["reason"])
        print(f"{marker} {name:20} {detail}")


def main(argv: Sequence[str] | None = None) -> int:
    """Execute the CLI and return a process exit code."""
    args = _parser().parse_args(list(argv) if argv is not None else None)

    if args.command == "status":
        _print_status(args.as_json)
        return 0

    if args.command == "serve":
        run_mcp()
        return 0

    if args.command == "search":
        try:
            result = ResearchService.from_environment().search(
                args.query,
                sources=_sources(args.sources),
                limit_per_source=args.limit_per_source,
                year=args.year,
            )
        except (ValueError, TypeError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(_json({"success": True, **result.to_dict()}))
        return 0

    return 2  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
