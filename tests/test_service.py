import asyncio

import pytest

from academic_research.mcp_server import ResearchTools, create_server
from academic_research.models import Author, Paper, SearchResult
from academic_research.service import ResearchService


class StubProvider:
    def __init__(self, source, papers=None, error=None):
        self.source = source
        self.papers = papers or []
        self.error = error
        self.calls = []

    def search(self, query, **kwargs):
        self.calls.append({"query": query, **kwargs})
        if self.error:
            raise self.error
        return SearchResult(
            source=self.source,
            provider=f"Stub {self.source}",
            query=query,
            total=len(self.papers),
            offset=0,
            limit=kwargs.get("limit", 10),
            papers=self.papers,
        )


def paper(
    source,
    identifier,
    title,
    *,
    doi=None,
    year=2025,
    abstract=None,
    citation_count=None,
    source_ids=None,
):
    return Paper(
        id=identifier,
        title=title,
        source=source,
        doi=doi,
        year=year,
        abstract=abstract,
        citation_count=citation_count,
        authors=[Author(name="Researcher")],
        source_ids=source_ids or {},
        provenance={"provider": f"Stub {source}"},
    )


def test_unified_search_deduplicates_and_preserves_multi_source_provenance():
    arxiv = StubProvider(
        "arxiv",
        [
            paper(
                "arxiv",
                "doi:10.1000/shared",
                "A Shared Academic Paper",
                doi="10.1000/shared",
                abstract=None,
                source_ids={"arxiv": "2501.00001v1", "doi": "10.1000/shared"},
            ),
            paper("arxiv", "arxiv:unique", "Unique Preprint", year=2026),
        ],
    )
    semantic = StubProvider(
        "semantic_scholar",
        [
            paper(
                "semantic_scholar",
                "doi:10.1000/shared",
                "A Shared Academic Paper",
                doi="10.1000/SHARED",
                abstract="The richer provider abstract.",
                citation_count=12,
                source_ids={"semantic_scholar": "s2-1", "doi": "10.1000/shared"},
            )
        ],
    )
    scopus = StubProvider("scopus", error=RuntimeError("quota exhausted"))
    service = ResearchService(
        providers={
            "arxiv": arxiv,
            "semantic_scholar": semantic,
            "scopus": scopus,
        }
    )

    result = service.search(
        "academic agents",
        sources=["arxiv", "semantic_scholar", "scopus"],
        limit_per_source=5,
    )
    payload = result.to_dict()

    assert result.retrieved_count == 3
    assert result.deduplicated_count == 2
    assert result.sources_succeeded == ["arxiv", "semantic_scholar"]
    assert result.sources_failed == ["scopus"]
    assert payload["errors"]["scopus"] == "RuntimeError: quota exhausted"

    shared = next(item for item in result.papers if item.doi == "10.1000/shared")
    assert shared.abstract == "The richer provider abstract."
    assert shared.citation_count == 12
    assert shared.source_ids == {
        "arxiv": "2501.00001v1",
        "doi": "10.1000/shared",
        "semantic_scholar": "s2-1",
    }
    assert shared.provenance["sources"] == ["arxiv", "semantic_scholar"]
    assert shared.metadata["citation_counts"] == {"semantic_scholar": 12}


def test_unified_search_falls_back_to_normalized_title_and_year():
    first = paper("arxiv", "arxiv:1", "Graph-Based   Research!", year=2024)
    second = paper(
        "semantic_scholar",
        "semantic_scholar:1",
        "graph based research",
        year=2024,
    )
    service = ResearchService(
        providers={
            "arxiv": StubProvider("arxiv", [first]),
            "semantic_scholar": StubProvider("semantic_scholar", [second]),
        }
    )

    result = service.search("graph research")

    assert result.retrieved_count == 2
    assert result.deduplicated_count == 1
    assert result.papers[0].provenance["dedupe_key"] == "title_year"


def test_unified_search_rejects_unknown_or_unavailable_sources():
    service = ResearchService(providers={"arxiv": StubProvider("arxiv")})

    with pytest.raises(ValueError, match="Unknown or unavailable source: pubmed"):
        service.search("test", sources=["pubmed"])


def test_unified_search_is_exposed_through_mcp():
    arxiv = StubProvider("arxiv", [paper("arxiv", "arxiv:1", "Paper")])
    service = ResearchService(providers={"arxiv": arxiv})
    tools = ResearchTools(service=service)

    payload = asyncio.run(tools.search_papers("academic agents", sources=["arxiv"]))
    assert payload["success"] is True
    assert payload["deduplicated_count"] == 1

    async def registered_names():
        return {tool.name for tool in await create_server(tools=tools).list_tools()}

    assert "search_papers" in asyncio.run(registered_names())
