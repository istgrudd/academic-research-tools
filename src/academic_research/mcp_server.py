"""MCP-facing tools backed by the harness-neutral academic research core."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from functools import wraps
from typing import Any

from .credentials import CredentialConfigError, CredentialResolver
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

_CONFIGURE_COMMANDS = {
    "scopus": "academic-research configure --provider scopus",
    "google_scholar": "academic-research configure --provider google-scholar",
}
_KNOWN_PROVIDERS = frozenset(
    {"arxiv", "semantic_scholar", "scopus", "google_scholar"}
)


def _credential_safe(method: Callable[..., Any]) -> Callable[..., Any]:
    """Return a secret-safe payload when credential configuration is invalid."""

    @wraps(method)
    async def wrapped(self, *args, **kwargs):
        try:
            return await method(self, *args, **kwargs)
        except CredentialConfigError:
            return {
                "success": False,
                "error": "Credential configuration is invalid; run the doctor command locally",
                "requires_user_action": True,
                "doctor_command": "academic-research doctor",
            }

    return wrapped


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
        resolver: CredentialResolver | None = None,
    ):
        self.credentials = resolver or CredentialResolver()
        self.arxiv = arxiv or ArxivProvider()
        self._semantic_scholar = semantic_scholar
        self._scopus = scopus
        self._google_scholar = google_scholar
        self.service = service

    def _semantic_provider(self) -> SemanticScholarProvider:
        return self._semantic_scholar or SemanticScholarProvider(
            self.credentials.get("SEMANTIC_SCHOLAR_API_KEY")
        )

    def _scopus_provider(self) -> ScopusProvider | None:
        if self._scopus is not None:
            return self._scopus
        api_key = self.credentials.get("ELSEVIER_API_KEY")
        if not api_key:
            return None
        return ScopusProvider(
            api_key,
            inst_token=self.credentials.get("ELSEVIER_INST_TOKEN"),
        )

    def _google_provider(self) -> SerpAPIScholarProvider | None:
        if self._google_scholar is not None:
            return self._google_scholar
        api_key = self.credentials.get("SERPAPI_API_KEY")
        return SerpAPIScholarProvider(api_key) if api_key else None

    def _research_service(self) -> ResearchService:
        if self.service is not None:
            return self.service
        providers: dict[str, Any] = {
            "arxiv": self.arxiv,
            "semantic_scholar": self._semantic_provider(),
        }
        scopus = self._scopus_provider()
        scholar = self._google_provider()
        if scopus is not None:
            providers["scopus"] = scopus
        if scholar is not None:
            providers["google_scholar"] = scholar
        return ResearchService(providers=providers, redact=self.credentials.redact)

    async def _run(self, operation: Callable[[], Any]) -> dict[str, Any]:
        try:
            result = await asyncio.to_thread(operation)
            payload = result.to_dict() if hasattr(result, "to_dict") else result
            return {"success": True, **payload}
        except _PROVIDER_ERRORS as exc:
            error = {"success": False, "error": self.credentials.redact(str(exc))}
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
                "error": self.credentials.redact(
                    f"Academic research tool failed: {type(exc).__name__}: {exc}"
                ),
            }

    @_credential_safe
    async def provider_status(self) -> dict[str, Any]:
        """Report configured providers without exposing secret values."""
        return {
            "success": True,
            "providers": provider_status(resolver=self.credentials),
        }

    @_credential_safe
    async def search_papers(
        self,
        query: str,
        sources: list[str] | None = None,
        limit_per_source: int = 10,
        year: str | int | None = None,
    ) -> dict[str, Any]:
        """Search available providers and degrade gracefully around optional ones."""
        service = self._research_service()
        if sources is None:
            return await self._run(
                lambda: service.search(
                    query,
                    sources=None,
                    limit_per_source=limit_per_source,
                    year=year,
                )
            )

        requested = list(dict.fromkeys(sources))
        unknown = [source for source in requested if source not in _KNOWN_PROVIDERS]
        if unknown:
            return {
                "success": False,
                "error": "Unknown source: " + ", ".join(unknown),
            }
        available = [source for source in requested if source in service.providers]
        unavailable = [source for source in requested if source not in service.providers]
        configuration = {
            source: _CONFIGURE_COMMANDS[source]
            for source in unavailable
            if source in _CONFIGURE_COMMANDS
        }
        if not available:
            payload: dict[str, Any] = {
                "success": False,
                "error": "Requested providers are not configured: "
                + ", ".join(unavailable),
                "requires_user_action": True,
                "configure_commands": configuration,
                "available_fallbacks": list(service.providers),
            }
            if len(configuration) == 1:
                payload["configure_command"] = next(iter(configuration.values()))
            return payload

        def search_available() -> dict[str, Any]:
            result = service.search(
                query,
                sources=available,
                limit_per_source=limit_per_source,
                year=year,
            ).to_dict()
            result["sources_requested"] = requested
            result["sources_failed"] = [*result["sources_failed"], *unavailable]
            for source in unavailable:
                result["errors"][source] = "Provider is not configured"
            if unavailable:
                result["warnings"].append(
                    "Optional providers were skipped: " + ", ".join(unavailable)
                )
            result["requires_user_action"] = False
            result["optional_configuration"] = configuration
            return result

        return await self._run(search_available)

    @_credential_safe
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

    @_credential_safe
    async def search_semantic_scholar(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        year: str | int | None = None,
    ) -> dict[str, Any]:
        """Search the official Semantic Scholar Academic Graph API."""
        semantic_scholar = self._semantic_provider()
        return await self._run(
            lambda: semantic_scholar.search(
                query, limit=limit, offset=offset, year=year
            )
        )

    @_credential_safe
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
        scopus = self._scopus_provider()
        if scopus is None:
            return {
                "success": False,
                "error": "ELSEVIER_API_KEY is not configured; see docs/providers/scopus.md",
                "authentication": "required",
                "requires_user_action": True,
                "configure_command": _CONFIGURE_COMMANDS["scopus"],
            }
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

    @_credential_safe
    async def get_scopus_abstract(
        self,
        identifier: str,
        identifier_type: str = "auto",
        view: str = "META_ABS",
    ) -> dict[str, Any]:
        """Retrieve normalized Scopus abstract metadata by DOI, EID, or ID."""
        scopus = self._scopus_provider()
        if scopus is None:
            return {
                "success": False,
                "error": "ELSEVIER_API_KEY is not configured; see docs/providers/scopus.md",
                "authentication": "required",
                "requires_user_action": True,
                "configure_command": _CONFIGURE_COMMANDS["scopus"],
            }
        return await self._run(
            lambda: scopus.get_abstract(
                identifier, identifier_type=identifier_type, view=view
            )
        )

    @_credential_safe
    async def search_scopus_authors(
        self, query: str, limit: int = 25, start: int = 0
    ) -> dict[str, Any]:
        """Search official Scopus author profiles."""
        scopus = self._scopus_provider()
        if scopus is None:
            return {
                "success": False,
                "error": "ELSEVIER_API_KEY is not configured; see docs/providers/scopus.md",
                "authentication": "required",
                "requires_user_action": True,
                "configure_command": _CONFIGURE_COMMANDS["scopus"],
            }
        return await self._run(
            lambda: scopus.search_authors(query, limit=limit, start=start)
        )

    @_credential_safe
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
        google_scholar = self._google_provider()
        if google_scholar is None:
            return {
                "success": False,
                "error": (
                    "SERPAPI_API_KEY is not configured; "
                    "see docs/providers/google-scholar-serpapi.md"
                ),
                "authentication": "required",
                "requires_user_action": True,
                "configure_command": _CONFIGURE_COMMANDS["google_scholar"],
            }
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
