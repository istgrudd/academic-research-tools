"""Credential-safe provider availability reporting."""

from __future__ import annotations

import os
from typing import Any


def _configured(name: str) -> bool:
    return bool(os.environ.get(name, "").strip())


def provider_status() -> dict[str, dict[str, Any]]:
    """Return provider capability state without returning any credential value."""
    semantic_authenticated = _configured("SEMANTIC_SCHOLAR_API_KEY")
    scopus_authenticated = _configured("ELSEVIER_API_KEY")
    institutional_token = _configured("ELSEVIER_INST_TOKEN")
    scholar_authenticated = _configured("SERPAPI_API_KEY")

    return {
        "arxiv": {
            "available": True,
            "authentication": "not_required",
            "authenticated": False,
        },
        "semantic_scholar": {
            "available": True,
            "authentication": "optional",
            "authenticated": semantic_authenticated,
            "reason": (
                None
                if semantic_authenticated
                else "SEMANTIC_SCHOLAR_API_KEY is optional but recommended for dedicated quota."
            ),
        },
        "scopus": {
            "available": scopus_authenticated,
            "authentication": "required",
            "authenticated": scopus_authenticated,
            "institutional_token": institutional_token,
            "reason": (
                None
                if scopus_authenticated
                else "ELSEVIER_API_KEY is not configured; only Scopus tools are disabled."
            ),
        },
        "google_scholar": {
            "available": scholar_authenticated,
            "authentication": "required",
            "authenticated": scholar_authenticated,
            "experimental": True,
            "reason": (
                None
                if scholar_authenticated
                else "SERPAPI_API_KEY is not configured; the optional SerpAPI adapter is disabled."
            ),
        },
    }
