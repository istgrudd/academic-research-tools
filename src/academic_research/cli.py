"""Command-line interface for Academic Research Tools."""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from collections.abc import Sequence
from typing import Any

from . import __version__
from .credentials import CredentialConfigError, CredentialResolver
from .doctor import doctor_report
from .integrations import IntegrationError, install_platform
from .mcp_server import main as run_mcp
from .service import ResearchService
from .status import provider_status

_CREDENTIAL_OPTIONS = {
    "scopus": ("Scopus / Elsevier", "ELSEVIER_API_KEY"),
    "semantic-scholar": ("Semantic Scholar", "SEMANTIC_SCHOLAR_API_KEY"),
    "google-scholar": ("Google Scholar via SerpAPI", "SERPAPI_API_KEY"),
    "scopus-institutional": ("Scopus institutional token", "ELSEVIER_INST_TOKEN"),
}
_SECRET_OPTION_WORDS = frozenset({"credential", "key", "password", "secret", "token"})


def _is_secret_option(token: str) -> bool:
    if not token.startswith("-"):
        return False
    option = token.split("=", 1)[0].lower().lstrip("-").replace("_", "-")
    words = set(option.split("-"))
    condensed = option.replace("-", "")
    return bool(words & _SECRET_OPTION_WORDS) or condensed.endswith(
        ("apikey", "accesstoken", "clientsecret", "insttoken")
    )


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

    configure_parser = subparsers.add_parser(
        "configure", help="Configure optional provider credentials interactively"
    )
    configure_actions = configure_parser.add_mutually_exclusive_group()
    configure_actions.add_argument(
        "--provider",
        choices=tuple(_CREDENTIAL_OPTIONS),
        help="Credential to configure; omit to choose from an interactive menu",
    )
    configure_actions.add_argument(
        "--remove",
        choices=tuple(_CREDENTIAL_OPTIONS),
        metavar="PROVIDER",
        help="Remove a saved credential without changing environment variables",
    )
    configure_actions.add_argument(
        "--list",
        action="store_true",
        dest="list_credentials",
        help="List provider availability without displaying credential values",
    )

    install_parser = subparsers.add_parser(
        "install", help="Register the MCP server and workflow skill for a coding agent"
    )
    install_parser.add_argument(
        "--platform",
        choices=("claude-code", "codex"),
        required=True,
        help="Host platform to configure",
    )

    doctor_parser = subparsers.add_parser(
        "doctor", help="Run credential-safe offline readiness checks"
    )
    doctor_parser.add_argument("--json", action="store_true", dest="as_json")

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


def _print_status(as_json: bool, *, resolver: CredentialResolver | None = None) -> None:
    statuses = provider_status(resolver=resolver)
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


def _read_secret(prompt: str) -> str:
    if not sys.stdin.isatty():
        raise CredentialConfigError(
            "Credential input requires an interactive terminal. "
            "Do not send API keys through chat or command arguments."
        )
    return getpass.getpass(prompt)


def _choose_credential() -> str | None:
    print("Academic Research Tools Configuration")
    print()
    for index, (_, (label, _)) in enumerate(_CREDENTIAL_OPTIONS.items(), start=1):
        print(f"  {index}. {label}")
    print("  0. Exit")
    print()
    selection = input("Selection: ").strip()
    if selection == "0":
        return None
    try:
        index = int(selection) - 1
        return tuple(_CREDENTIAL_OPTIONS)[index] if index >= 0 else None
    except (ValueError, IndexError) as exc:
        raise CredentialConfigError("Invalid credential selection") from exc


def _configure(args: argparse.Namespace) -> int:
    resolver = CredentialResolver()
    if args.list_credentials:
        _print_status(False, resolver=resolver)
        return 0
    if args.remove:
        label, name = _CREDENTIAL_OPTIONS[args.remove]
        removed = resolver.remove(name)
        if removed:
            print(f"✓ Removed saved credential for {label}.")
        else:
            print(f"○ No saved credential found for {label}.")
        if resolver.source(name) == "environment":
            print("  An environment variable remains active and was not modified.")
        return 0

    provider = args.provider or _choose_credential()
    if provider is None:
        return 0
    label, name = _CREDENTIAL_OPTIONS[provider]
    value = _read_secret(f"{label} credential: ")
    resolver.set(name, value)
    print(f"✓ Credential saved locally for {label}.")
    print("  Run `academic-research status` to verify provider availability.")
    return 0


def _install(platform: str) -> int:
    result = install_platform(platform)
    host = "Claude Code" if platform == "claude-code" else "Codex"
    print(f"✓ Academic Research Tools registered for {host}.")
    print(f"✓ Workflow skill installed at {result['skill_path']}.")
    print()
    print("Ready now: arXiv and Semantic Scholar public access.")
    print("Optionally, run `academic-research configure` later to enable")
    print("Scopus, dedicated Semantic Scholar quota, or Google Scholar via SerpAPI.")
    return 0


def _doctor(as_json: bool) -> int:
    report = doctor_report(resolver=CredentialResolver())
    if as_json:
        print(_json(report))
    else:
        marker = "✓" if report["ready_for_search"] else "✗"
        print(f"{marker} Ready for search: {report['ready_for_search']}")
        credentials = report["credentials"]
        config_marker = "✓" if credentials["config_valid"] else "✗"
        print(f"{config_marker} Credential config valid: {credentials['config_valid']}")
        print(f"  Path: {credentials['config_path']}")
        if credentials["error"]:
            print(f"  Error: {credentials['error']}")
        print()
        print("Optional: academic-research configure")
    return 0 if report["success"] else 1


def main(argv: Sequence[str] | None = None) -> int:
    """Execute the CLI and return a process exit code."""
    arguments = list(argv) if argv is not None else sys.argv[1:]
    if any(_is_secret_option(token) for token in arguments):
        print(
            "Credential arguments are not supported. Enter credentials only through "
            "`academic-research configure` in an interactive terminal.",
            file=sys.stderr,
        )
        return 2
    args = _parser().parse_args(arguments)

    try:
        if args.command == "status":
            _print_status(args.as_json)
            return 0

        if args.command == "configure":
            return _configure(args)

        if args.command == "install":
            return _install(args.platform)

        if args.command == "doctor":
            return _doctor(args.as_json)

        if args.command == "serve":
            run_mcp()
            return 0

        if args.command == "search":
            result = ResearchService.from_environment().search(
                args.query,
                sources=_sources(args.sources),
                limit_per_source=args.limit_per_source,
                year=args.year,
            )
            print(_json({"success": True, **result.to_dict()}))
            return 0
    except (
        CredentialConfigError,
        IntegrationError,
        ValueError,
        TypeError,
        EOFError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Configuration cancelled.", file=sys.stderr)
        return 130

    return 2  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
