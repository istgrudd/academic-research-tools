"""Native Hermes Agent adapter for Academic Research Tools."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .hermes_schemas import SCHEMAS
from .mcp_server import ResearchTools

_TOOLSETS = {
    "research_provider_status": "academic-research",
    "search_papers": "academic-research",
    "search_arxiv": "arxiv",
    "search_semantic_scholar": "semantic-scholar",
    "search_scopus": "scopus",
    "get_scopus_abstract": "scopus",
    "search_scopus_authors": "scopus",
    "search_google_scholar": "scholar",
}

_EMOJI = {
    "research_provider_status": "🧪",
    "search_papers": "🔎",
    "search_arxiv": "🗄️",
    "search_semantic_scholar": "🔬",
    "search_scopus": "📚",
    "get_scopus_abstract": "📄",
    "search_scopus_authors": "🧑‍🔬",
    "search_google_scholar": "🎓",
}

_METHODS = {
    "research_provider_status": "provider_status",
    "search_papers": "search_papers",
    "search_arxiv": "search_arxiv",
    "search_semantic_scholar": "search_semantic_scholar",
    "search_scopus": "search_scopus",
    "get_scopus_abstract": "get_scopus_abstract",
    "search_scopus_authors": "search_scopus_authors",
    "search_google_scholar": "search_google_scholar",
}


def _configured(name: str) -> bool:
    return bool(os.environ.get(name, "").strip())


def _handler(method_name: str) -> Callable[..., str]:
    def handle(args: dict[str, Any], **kwargs: Any) -> str:
        del kwargs
        try:
            method = getattr(ResearchTools(), method_name)
            result = asyncio.run(method(**dict(args or {})))
        except Exception as exc:  # Hermes handlers must return structured failures
            result = {
                "success": False,
                "error": f"Academic research tool failed: {type(exc).__name__}: {exc}",
            }
        return json.dumps(result, ensure_ascii=False)

    return handle


def register(ctx: Any) -> None:
    """Register native tools and the screening skill with Hermes Agent."""
    for name, schema in SCHEMAS.items():
        kwargs: dict[str, Any] = {
            "name": name,
            "toolset": _TOOLSETS[name],
            "schema": schema,
            "handler": _handler(_METHODS[name]),
            "description": schema["description"],
            "emoji": _EMOJI[name],
        }
        if name in {"search_scopus", "get_scopus_abstract", "search_scopus_authors"}:
            kwargs["check_fn"] = lambda: _configured("ELSEVIER_API_KEY")
        elif name == "search_google_scholar":
            kwargs["check_fn"] = lambda: _configured("SERPAPI_API_KEY")
        ctx.register_tool(**kwargs)

    skill_path = (
        Path(__file__).parent
        / "skills"
        / "academic-research-workflow"
        / "SKILL.md"
    )
    if skill_path.exists():
        ctx.register_skill("academic-research-workflow", skill_path)
