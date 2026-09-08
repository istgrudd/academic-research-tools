"""Scopus Research plugin registration."""

from pathlib import Path

from .schemas import (
    ARXIV_SEARCH_SCHEMA,
    GOOGLE_SCHOLAR_SEARCH_SCHEMA,
    SCOPUS_ABSTRACT_SCHEMA,
    SCOPUS_AUTHOR_SEARCH_SCHEMA,
    SCOPUS_SEARCH_SCHEMA,
    SEMANTIC_SCHOLAR_SEARCH_SCHEMA,
)
from .tools import (
    handle_arxiv_search,
    handle_google_scholar_search,
    handle_scopus_abstract,
    handle_scopus_author_search,
    handle_scopus_search,
    handle_semantic_scholar_search,
)


def _scopus_available() -> bool:
    import os
    return bool(os.environ.get("ELSEVIER_API_KEY", "").strip())


def _scholar_available() -> bool:
    import os
    return bool(os.environ.get("SERPAPI_API_KEY", "").strip())


def register(ctx) -> None:
    ctx.register_tool(
        name="arxiv_search",
        toolset="arxiv",
        schema=ARXIV_SEARCH_SCHEMA,
        handler=handle_arxiv_search,
        description="Search and retrieve papers through the official public arXiv API.",
        emoji="🗄️",
    )
    ctx.register_tool(
        name="semantic_scholar_search",
        toolset="semantic-scholar",
        schema=SEMANTIC_SCHOLAR_SEARCH_SCHEMA,
        handler=handle_semantic_scholar_search,
        description="Search the official Semantic Scholar Academic Graph API.",
        emoji="🔬",
    )
    ctx.register_tool(
        name="scopus_search",
        toolset="scopus",
        schema=SCOPUS_SEARCH_SCHEMA,
        handler=handle_scopus_search,
        check_fn=_scopus_available,
        description="Search Scopus-indexed literature through the official Elsevier API.",
        emoji="📚",
    )
    ctx.register_tool(
        name="scopus_abstract",
        toolset="scopus",
        schema=SCOPUS_ABSTRACT_SCHEMA,
        handler=handle_scopus_abstract,
        check_fn=_scopus_available,
        description="Retrieve a Scopus abstract and normalized metadata.",
        emoji="📄",
    )
    ctx.register_tool(
        name="scopus_author_search",
        toolset="scopus",
        schema=SCOPUS_AUTHOR_SEARCH_SCHEMA,
        handler=handle_scopus_author_search,
        check_fn=_scopus_available,
        description="Search Scopus author profiles.",
        emoji="🧑‍🔬",
    )
    ctx.register_tool(
        name="google_scholar_search",
        toolset="scholar",
        schema=GOOGLE_SCHOLAR_SEARCH_SCHEMA,
        handler=handle_google_scholar_search,
        check_fn=_scholar_available,
        description="Search Google Scholar through the optional SerpAPI provider.",
        emoji="🎓",
    )
    skill_path = Path(__file__).parent / "skills" / "literature-screening" / "SKILL.md"
    if skill_path.exists():
        ctx.register_skill("literature-screening", skill_path)
