"""Offline diagnostics for installation and credential readiness."""

from __future__ import annotations

import os
import stat
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .credentials import CredentialConfigError, CredentialResolver
from .providers.arxiv import ArxivProvider
from .providers.scopus import ScopusProvider
from .providers.semantic_scholar import SemanticScholarProvider
from .providers.serpapi_scholar import SerpAPIScholarProvider
from .status import provider_status

ONLINE_TIMEOUT_SECONDS = 10
# One small, stable query per provider; each check sends exactly one request.
_PROBE_QUERIES = {
    "arxiv": "all:electron",
    "semantic_scholar": "transformer",
    "scopus": "TITLE(transformer)",
    "google_scholar": "transformer",
}


class _EnvironmentOnlyResolver(CredentialResolver):
    """Resolve only environment values when the on-disk config is invalid."""

    def _load(self) -> dict[str, str]:
        return {}


def _permissions_private(path: Path) -> bool:
    if os.name == "nt" or not path.exists():
        return True
    return stat.S_IMODE(path.stat().st_mode) & 0o077 == 0


def online_providers(resolver: CredentialResolver) -> dict[str, Any]:
    """Build active providers for single-request reachability checks."""
    timeout = float(ONLINE_TIMEOUT_SECONDS)
    providers: dict[str, Any] = {
        "arxiv": ArxivProvider(timeout=timeout, max_retries=0),
        "semantic_scholar": SemanticScholarProvider(
            resolver.get("SEMANTIC_SCHOLAR_API_KEY"), timeout=timeout, max_retries=0
        ),
    }
    elsevier_key = resolver.get("ELSEVIER_API_KEY")
    if elsevier_key:
        providers["scopus"] = ScopusProvider(
            elsevier_key,
            inst_token=resolver.get("ELSEVIER_INST_TOKEN"),
            timeout=timeout,
        )
    serpapi_key = resolver.get("SERPAPI_API_KEY")
    if serpapi_key:
        providers["google_scholar"] = SerpAPIScholarProvider(serpapi_key, timeout=timeout)
    return providers


def _probe(source: str, provider: Any, redact: Callable[[str], str]) -> dict[str, Any]:
    started = time.monotonic()
    try:
        provider.search(_PROBE_QUERIES.get(source, "transformer"), limit=1)
    except Exception as exc:  # report every failure as a diagnostic, never raise
        error: str | None = redact(f"{type(exc).__name__}: {exc}")
    else:
        error = None
    return {
        "reachable": error is None,
        "elapsed_ms": int((time.monotonic() - started) * 1000),
        "error": error,
    }


def _online_checks(providers: dict[str, Any], redact: Callable[[str], str]) -> dict[str, Any]:
    results: dict[str, dict[str, Any]] = {}
    if providers:
        with ThreadPoolExecutor(max_workers=min(len(providers), 4)) as executor:
            futures = {
                source: executor.submit(_probe, source, provider, redact)
                for source, provider in providers.items()
            }
            results = {source: future.result() for source, future in futures.items()}
    return {
        "timeout_seconds": ONLINE_TIMEOUT_SECONDS,
        "all_reachable": bool(results) and all(item["reachable"] for item in results.values()),
        "providers": results,
    }


def doctor_report(
    *,
    resolver: CredentialResolver | None = None,
    online: bool = False,
    online_providers_factory: Callable[[CredentialResolver], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return credential-safe diagnostics; contact providers only when ``online``."""
    credentials = resolver or CredentialResolver()
    config_exists = credentials.config_path.exists()
    config_valid = True
    config_error: str | None = None

    active_resolver = credentials
    try:
        sources = credentials.list_sources()
        providers = provider_status(resolver=credentials)
    except CredentialConfigError as exc:
        config_valid = False
        config_error = str(exc)
        fallback = _EnvironmentOnlyResolver(
            config_path=credentials.config_path,
            environ=credentials.environ,
        )
        active_resolver = fallback
        sources = fallback.list_sources()
        providers = provider_status(resolver=fallback)

    permissions_private = _permissions_private(credentials.config_path)
    ready_for_search = any(item["available"] for item in providers.values())
    configured_count = sum(source is not None for source in sources.values())
    success = config_valid and permissions_private and ready_for_search

    online_report: dict[str, Any] | None = None
    if online:
        factory = online_providers_factory or online_providers
        online_report = _online_checks(factory(active_resolver), active_resolver.redact)
        success = success and online_report["all_reachable"]

    report: dict[str, Any] = {
        "success": success,
        "ready_for_search": ready_for_search,
        "credentials": {
            "config_path": str(credentials.config_path),
            "config_exists": config_exists,
            "config_valid": config_valid,
            "permissions_private": permissions_private,
            "configured_count": configured_count,
            "error": config_error,
        },
        "providers": providers,
        "onboarding": {
            "configuration_required": False,
            "optional_command": "academic-research configure",
            "message": (
                "Optional credentials enable additional providers or dedicated quota."
            ),
        },
    }
    if online_report is not None:
        report["online"] = online_report
    return report
