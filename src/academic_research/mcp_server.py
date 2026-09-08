"""MCP-facing tool methods backed by the harness-neutral research core."""

from __future__ import annotations

import asyncio
from typing import Any

from .providers.arxiv import ArxivAPIError, ArxivProvider
from .status import provider_status


class ResearchTools:
    """JSON-safe async facade shared by the MCP server and protocol tests."""

    def __init__(self, *, arxiv: ArxivProvider | None = None):
        self.arxiv = arxiv or ArxivProvider()

    async def provider_status(self) -> dict[str, Any]:
        """Report configured providers without exposing secret values."""
        return {"success": True, "providers": provider_status()}

    async def search_arxiv(
        self,
        query: str | None = None,
        ids: list[str] | str | None = None,
        limit: int = 10,
        start: int = 0,
        sort_by: str = "relevance",
        sort_order: str = "descending",
    ) -> dict[str, Any]:
        """Search arXiv through its official public API."""
        try:
            result = await asyncio.to_thread(
                self.arxiv.search,
                query,
                ids=ids,
                limit=limit,
                start=start,
                sort_by=sort_by,
                sort_order=sort_order,
            )
            return {"success": True, **result.to_dict()}
        except (ArxivAPIError, ValueError, TypeError) as exc:
            return {
                "success": False,
                "error": str(exc),
                "status_code": getattr(exc, "status_code", None),
            }


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
    server.add_tool(
        facade.provider_status,
        name="research_provider_status",
        description="Report academic provider availability without exposing credentials.",
    )
    server.add_tool(
        facade.search_arxiv,
        name="search_arxiv",
        description="Search and retrieve papers through the official public arXiv API.",
    )
    return server


def main() -> None:
    """Run the MCP server over stdio."""
    create_server().run(transport="stdio")


if __name__ == "__main__":  # pragma: no cover
    main()
