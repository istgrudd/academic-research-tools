"""Offline diagnostics for installation and credential readiness."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any

from .credentials import CredentialConfigError, CredentialResolver
from .status import provider_status


class _EnvironmentOnlyResolver(CredentialResolver):
    """Resolve only environment values when the on-disk config is invalid."""

    def _load(self) -> dict[str, str]:
        return {}


def _permissions_private(path: Path) -> bool:
    if os.name == "nt" or not path.exists():
        return True
    return stat.S_IMODE(path.stat().st_mode) & 0o077 == 0


def doctor_report(
    *, resolver: CredentialResolver | None = None
) -> dict[str, Any]:
    """Return credential-safe, network-free health diagnostics."""
    credentials = resolver or CredentialResolver()
    config_exists = credentials.config_path.exists()
    config_valid = True
    config_error: str | None = None

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
        sources = fallback.list_sources()
        providers = provider_status(resolver=fallback)

    permissions_private = _permissions_private(credentials.config_path)
    ready_for_search = any(item["available"] for item in providers.values())
    configured_count = sum(source is not None for source in sources.values())
    success = config_valid and permissions_private and ready_for_search

    return {
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
