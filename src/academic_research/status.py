"""Credential-safe provider availability reporting."""

from __future__ import annotations

from typing import Any

from .credentials import CredentialResolver


def provider_status(
    *, resolver: CredentialResolver | None = None
) -> dict[str, dict[str, Any]]:
    """Return provider capability state without returning any credential value."""
    credentials = resolver or CredentialResolver()
    semantic_key = credentials.get("SEMANTIC_SCHOLAR_API_KEY")
    elsevier_key = credentials.get("ELSEVIER_API_KEY")
    institutional_token = credentials.get("ELSEVIER_INST_TOKEN")
    serpapi_key = credentials.get("SERPAPI_API_KEY")

    semantic_configured = bool(semantic_key)
    scopus_configured = bool(elsevier_key)
    scholar_configured = bool(serpapi_key)

    return {
        "arxiv": {
            "available": True,
            "authentication": "not_required",
            "authenticated": False,
            "credential_requirement": "none",
            "blocks_initial_setup": False,
            "configure_command": None,
            "recommendation": None,
        },
        "semantic_scholar": {
            "available": True,
            "authentication": "optional",
            "authenticated": semantic_configured,
            "configured": semantic_configured,
            "credential_source": credentials.source("SEMANTIC_SCHOLAR_API_KEY"),
            "credential_requirement": "optional",
            "blocks_initial_setup": False,
            "configure_command": (
                None
                if semantic_configured
                else "academic-research configure --provider semantic-scholar"
            ),
            "reason": (
                None
                if semantic_configured
                else "An API key is optional but recommended for dedicated quota."
            ),
            "recommendation": (
                None
                if semantic_configured
                else "Optionally configure a key for dedicated Semantic Scholar quota."
            ),
        },
        "scopus": {
            "available": scopus_configured,
            "authentication": "required",
            "authenticated": scopus_configured,
            "configured": scopus_configured,
            "credential_source": credentials.source("ELSEVIER_API_KEY"),
            "credential_requirement": "required",
            "institutional_token": bool(institutional_token),
            "blocks_initial_setup": False,
            "configure_command": (
                None
                if scopus_configured
                else "academic-research configure --provider scopus"
            ),
            "reason": (
                None
                if scopus_configured
                else "Scopus is optional and disabled until ELSEVIER_API_KEY is configured."
            ),
            "recommendation": (
                None
                if scopus_configured
                else "Configure Scopus only when its indexed coverage is needed."
            ),
        },
        "google_scholar": {
            "available": scholar_configured,
            "authentication": "required",
            "authenticated": scholar_configured,
            "configured": scholar_configured,
            "credential_source": credentials.source("SERPAPI_API_KEY"),
            "credential_requirement": "required",
            "experimental": True,
            "blocks_initial_setup": False,
            "configure_command": (
                None
                if scholar_configured
                else "academic-research configure --provider google-scholar"
            ),
            "reason": (
                None
                if scholar_configured
                else "The optional SerpAPI adapter is disabled until configured."
            ),
            "recommendation": (
                None
                if scholar_configured
                else "Configure SerpAPI only when Google Scholar coverage is needed."
            ),
        },
    }
