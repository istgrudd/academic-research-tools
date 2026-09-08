import asyncio

from academic_research.mcp_server import ResearchTools, create_server
from academic_research.models import Paper, SearchResult


class StubSearchProvider:
    def __init__(self, source: str):
        self.source = source
        self.calls = []

    def search(self, query, **kwargs):
        self.calls.append({"query": query, **kwargs})
        return SearchResult(
            source=self.source,
            provider=f"Stub {self.source}",
            query=query,
            total=1,
            offset=0,
            limit=kwargs.get("limit", 10),
            papers=[
                Paper(
                    id=f"{self.source}:1",
                    title="Stub paper",
                    source=self.source,
                )
            ],
        )


class StubScopusProvider(StubSearchProvider):
    def get_abstract(self, identifier, **kwargs):
        return {
            "identifier": identifier,
            "identifier_type": kwargs.get("identifier_type", "auto"),
            "paper": {
                "id": "doi:10.1/example",
                "title": "Detail",
                "source": "scopus",
            },
        }

    def search_authors(self, query, **kwargs):
        return {
            "source": "scopus",
            "query": query,
            "results": [{"author_id": "1", "name": "Researcher"}],
        }


def test_server_registers_all_public_academic_tools(monkeypatch):
    monkeypatch.delenv("ELSEVIER_API_KEY", raising=False)
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)

    async def exercise():
        names = {tool.name for tool in await create_server().list_tools()}
        assert names == {
            "research_provider_status",
            "search_arxiv",
            "search_semantic_scholar",
            "search_scopus",
            "get_scopus_abstract",
            "search_scopus_authors",
            "search_google_scholar",
        }

    asyncio.run(exercise())


def test_missing_scopus_key_returns_actionable_error_without_secret(monkeypatch):
    monkeypatch.delenv("ELSEVIER_API_KEY", raising=False)
    tools = ResearchTools()
    payload = asyncio.run(tools.search_scopus("traffic flow"))

    assert payload["success"] is False
    assert "ELSEVIER_API_KEY" in payload["error"]
    assert set(payload) == {"success", "error"}


def test_provider_specific_tools_use_injected_core_providers():
    semantic = StubSearchProvider("semantic_scholar")
    scopus = StubScopusProvider("scopus")
    scholar = StubSearchProvider("google_scholar")
    tools = ResearchTools(
        semantic_scholar=semantic,
        scopus=scopus,
        google_scholar=scholar,
    )

    semantic_payload = asyncio.run(
        tools.search_semantic_scholar("agentic research", limit=3, year="2024-2026")
    )
    scopus_payload = asyncio.run(tools.search_scopus("TITLE-ABS-KEY(agent)", limit=4))
    detail_payload = asyncio.run(tools.get_scopus_abstract("10.1/example"))
    author_payload = asyncio.run(tools.search_scopus_authors("AUTHLASTNAME(Smith)"))
    scholar_payload = asyncio.run(tools.search_google_scholar("agentic research", limit=5))

    assert semantic_payload["success"] is True
    assert semantic.calls[0]["year"] == "2024-2026"
    assert scopus_payload["results"][0]["source"] == "scopus"
    assert detail_payload["paper"]["title"] == "Detail"
    assert author_payload["results"][0]["name"] == "Researcher"
    assert scholar_payload["results"][0]["source"] == "google_scholar"
