"""MCP-facing tools backed by the harness-neutral academic research core."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from typing import Any

from .providers.arxiv import ArxivAPIError, ArxivProvider
from .providers.scopus import ElsevierAPIError, ScopusProvider
from .providers.semantic_scholar import (
    SemanticScholarAPIError,
    SemanticScholarProvider,
)
from .providers.serpapi_scholar import SerpAPIError, SerpAPIScholarProvider
from .service import ResearchService
from .status import provider_status

_PROVIDER_ERRORS = (
    ArxivAPIError,
    ElsevierAPIError,
    SemanticScholarAPIError,
    SerpAPIError,
    ValueError,
    TypeError,
)


class ResearchTools:
    """Async facade that keeps blocking provider clients off the event loop."""

    def __init__(
        self,
        *,
        arxiv: ArxivProvider | None = None,
        semantic_scholar: SemanticScholarProvider | None = None,
        scopus: ScopusProvider | None = None,
        google_scholar: SerpAPIScholarProvider | None = None,
        service: ResearchService | None = None,
    ):
        self.arxiv = arxiv or ArxivProvider()
        self.semantic_scholar = semantic_scholar or SemanticScholarProvider(
            os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
        )
        elsevier_key = os.environ.get("ELSEVIER_API_KEY", "").strip()
        self.scopus = scopus or (
            ScopusProvider(
                elsevier_key,
                inst_token=os.environ.get("ELSEVIER_INST_TOKEN"),
            )
            if elsevier_key
            else None
        )
        serpapi_key = os.environ.get("SERPAPI_API_KEY", "").strip()
        self.google_scholar = google_scholar or (
            SerpAPIScholarProvider(serpapi_key) if serpapi_key else None
        )
        self.service = service or ResearchService(
            providers={
                name: provider
                for name, provider in {
                    "arxiv": self.arxiv,
                    "semantic_scholar": self.semantic_scholar,
                    "scopus": self.scopus,
                    "google_scholar": self.google_scholar,
                }.items()
                if provider is not None
            }
        )

    async def _run(self, operation: Callable[[], Any]) -> dict[str, Any]:
        try:
            result = await asyncio.to_thread(operation)
            payload = result.to_dict() if hasattr(result, "to_dict") else result
            return {"success": True, **payload}
        except _PROVIDER_ERRORS as exc:
            error = {"success": False, "error": str(exc)}
            status_code = getattr(exc, "status_code", None)
            quota = getattr(exc, "quota", None)
            if status_code is not None:
                error["status_code"] = status_code
            if quota:
                error["quota"] = quota
            return error
        except Exception as exc:  # defensive tool boundary
            return {
                "success": False,
                "error": f"Academic research tool failed: {type(exc).__name__}: {exc}",
            }

    async def provider_status(self) -> dict[str, Any]:
        """Report configured providers without exposing secret values."""
        return {"success": True, "providers": provider_status()}

    async def search_papers(
        self,
        query: str,
        sources: list[str] | None = None,
        limit_per_source: int = 10,
        year: str | int | None = None,
    ) -> dict[str, Any]:
        """Search multiple scholarly providers and deduplicate the results."""
        return await self._run(
            lambda: self.service.search(
                query,
                sources=sources,
                limit_per_source=limit_per_source,
                year=year,
            )
        )

    async def search_arxiv(
        self,
        query: str | None = None,
        ids: list[str] | str | None = None,
        limit: int = 10,
        start: int = 0,
        sort_by: str = "relevance",
        sort_order: str = "descending",
    ) -> dict[str, Any]:
        """Search the official public arXiv API."""
        return await self._run(
            lambda: self.arxiv.search(
                query,
                ids=ids,
                limit=limit,
                start=start,
                sort_by=sort_by,
                sort_order=sort_order,
            )
        )

    async def search_semantic_scholar(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        year: str | int | None = None,
    ) -> dict[str, Any]:
        """Search the official Semantic Scholar Academic Graph API."""
        return await self._run(
            lambda: self.semantic_scholar.search(
                query, limit=limit, offset=offset, year=year
            )
        )

    async def search_scopus(
        self,
        query: str,
        limit: int = 25,
        start: int = 0,
        sort: str | None = None,
        view: str = "STANDARD",
        date: str | None = None,
        subject_area: str | None = None,
        fields: str | None = None,
        facets: str | None = None,
        content: str = "all",
    ) -> dict[str, Any]:
        """Search Scopus using the user's Elsevier API credentials."""
        if self.scopus is None:
            return {
                "success": False,
                "error": "ELSEVIER_API_KEY is not configured; see docs/providers/scopus.md",
            }
        scopus = self.scopus
        return await self._run(
            lambda: scopus.search(
                query,
                limit=limit,
                start=start,
                sort=sort,
                view=view,
                date=date,
                subject_area=subject_area,
                fields=fields,
                facets=facets,
                content=content,
            )
        )

    async def get_scopus_abstract(
        self,
        identifier: str,
        identifier_type: str = "auto",
        view: str = "META_ABS",
    ) -> dict[str, Any]:
        """Retrieve normalized Scopus abstract metadata by DOI, EID, or ID."""
        if self.scopus is None:
            return {
                "success": False,
                "error": "ELSEVIER_API_KEY is not configured; see docs/providers/scopus.md",
            }
        scopus = self.scopus
        return await self._run(
            lambda: scopus.get_abstract(
                identifier, identifier_type=identifier_type, view=view
            )
        )

    async def search_scopus_authors(
        self, query: str, limit: int = 25, start: int = 0
    ) -> dict[str, Any]:
        """Search official Scopus author profiles."""
        if self.scopus is None:
            return {
                "success": False,
                "error": "ELSEVIER_API_KEY is not configured; see docs/providers/scopus.md",
            }
        scopus = self.scopus
        return await self._run(
            lambda: scopus.search_authors(query, limit=limit, start=start)
        )

    async def search_google_scholar(
        self,
        query: str,
        limit: int = 10,
        start: int = 0,
        year_from: int | None = None,
        year_to: int | None = None,
        language: str = "en",
        sort_by_date: bool = False,
    ) -> dict[str, Any]:
        """Search Google Scholar through optional third-party SerpAPI."""
        if self.google_scholar is None:
            return {
                "success": False,
                "error": "SERPAPI_API_KEY is not configured; see docs/providers/serpapi.md",
            }
        google_scholar = self.google_scholar
        return await self._run(
            lambda: google_scholar.search(
                query,
                limit=limit,
                start=start,
                year_from=year_from,
                year_to=year_to,
                language=language,
                sort_by_date=sort_by_date,
            )
        )


def create_server(*, tools: ResearchTools | None = None):
    """Create the official MCP SDK server without coupling providers to MCP."""
    try:
        from mcp.server import MCPServer
    except ImportError as exc:  # pragma: no cover - packaging guards this path
        raise RuntimeError(
            "MCP support is not installed. Install academic-research-tools[mcp]."
        ) from exc

    facade = tools or ResearchTools()
    server = MCPServer(
        "Academic Research Tools",
        instructions=(
            "Search scholarly sources and preserve source provenance. "
            "Do not treat citation count as evidence of relevance or quality."
        ),
    )
    registrations = [
        (
            facade.provider_status,
            "research_provider_status",
            "Report provider availability without exposing credentials.",
        ),
        (
            facade.search_papers,
            "search_papers",
            "Search available scholarly providers with provenance-aware deduplication.",
        ),
        (
            facade.search_arxiv,
            "search_arxiv",
            "Search and retrieve papers through the official public arXiv API.",
        ),
        (
            facade.search_semantic_scholar,
            "search_semantic_scholar",
            "Search the official Semantic Scholar Academic Graph API.",
        ),
        (
            facade.search_scopus,
            "search_scopus",
            "Search Scopus-indexed literature through the official Elsevier API.",
        ),
        (
            facade.get_scopus_abstract,
            "get_scopus_abstract",
            "Retrieve a Scopus abstract and normalized paper metadata.",
        ),
        (
            facade.search_scopus_authors,
            "search_scopus_authors",
            "Search official Scopus author profiles.",
        ),
        (
            facade.search_google_scholar,
            "search_google_scholar",
            "Search Google Scholar through optional third-party SerpAPI.",
        ),
    ]
    for function, name, description in registrations:
        server.add_tool(function, name=name, description=description)
    return server


def main() -> None:
    """Run the MCP server over stdio."""
    create_server().run(transport="stdio")


if __name__ == "__main__":  # pragma: no cover
    main()
