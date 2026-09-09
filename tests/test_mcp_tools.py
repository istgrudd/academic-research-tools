import asyncio
import json

from academic_research.credentials import CredentialResolver
from academic_research.mcp_server import ResearchTools, create_server
from academic_research.models import Paper, SearchResult
from academic_research.providers.serpapi_scholar import SerpAPIScholarProvider


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
            "search_papers",
            "search_arxiv",
            "search_semantic_scholar",
            "search_scopus",
            "get_scopus_abstract",
            "search_scopus_authors",
            "search_google_scholar",
        }

    asyncio.run(exercise())


def test_missing_scopus_key_returns_actionable_error_without_secret(tmp_path):
    resolver = CredentialResolver(config_path=tmp_path / "credentials.json", environ={})
    tools = ResearchTools(resolver=resolver)
    payload = asyncio.run(tools.search_scopus("traffic flow"))

    assert payload["success"] is False
    assert "ELSEVIER_API_KEY" in payload["error"]
    assert payload["authentication"] == "required"
    assert payload["requires_user_action"] is True
    assert payload["configure_command"] == (
        "academic-research configure --provider scopus"
    )


def test_invalid_credential_config_returns_safe_actionable_mcp_error(tmp_path):
    config_path = tmp_path / "credentials.json"
    config_path.write_text('{"secret":"must-not-leak"')
    config_path.chmod(0o600)
    tools = ResearchTools(
        resolver=CredentialResolver(config_path=config_path, environ={})
    )

    payloads = [
        asyncio.run(tools.provider_status()),
        asyncio.run(tools.search_papers("traffic flow")),
        asyncio.run(tools.search_scopus("traffic flow")),
    ]

    for payload in payloads:
        assert payload["success"] is False
        assert payload["requires_user_action"] is True
        assert payload["doctor_command"] == "academic-research doctor"
        assert "must-not-leak" not in json.dumps(payload)


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


def test_mcp_detects_new_saved_credential_without_process_restart(monkeypatch, tmp_path):
    resolver = CredentialResolver(config_path=tmp_path / "credentials.json", environ={})
    scopus = StubScopusProvider("scopus")
    monkeypatch.setattr(
        "academic_research.mcp_server.ScopusProvider",
        lambda api_key, inst_token=None: scopus,
    )
    tools = ResearchTools(resolver=resolver)

    unavailable = asyncio.run(tools.search_scopus("traffic flow"))
    resolver.set("ELSEVIER_API_KEY", "newly-saved-secret")
    available = asyncio.run(tools.search_scopus("traffic flow"))

    assert unavailable["success"] is False
    assert unavailable["requires_user_action"] is True
    assert unavailable["configure_command"] == (
        "academic-research configure --provider scopus"
    )
    assert available["success"] is True
    assert scopus.calls[0]["query"] == "traffic flow"


def test_unified_mcp_search_keeps_available_results_when_optional_source_is_missing(
    tmp_path,
):
    resolver = CredentialResolver(config_path=tmp_path / "credentials.json", environ={})
    arxiv = StubSearchProvider("arxiv")
    tools = ResearchTools(arxiv=arxiv, resolver=resolver)

    payload = asyncio.run(
        tools.search_papers("traffic flow", sources=["arxiv", "scopus"])
    )

    assert payload["success"] is True
    assert payload["sources_succeeded"] == ["arxiv"]
    assert payload["sources_failed"] == ["scopus"]
    assert payload["requires_user_action"] is False
    assert payload["optional_configuration"]["scopus"] == (
        "academic-research configure --provider scopus"
    )


def test_mcp_redacts_credentials_from_provider_errors(tmp_path):
    class FailingProvider(SerpAPIScholarProvider):
        def __init__(self):
            super().__init__("key/with space")

        def search(self, query, **kwargs):
            raise RuntimeError("failed URL contained key%2Fwith+space")

    resolver = CredentialResolver(config_path=tmp_path / "credentials.json", environ={})
    resolver.set("SERPAPI_API_KEY", "key/with space")
    tools = ResearchTools(google_scholar=FailingProvider(), resolver=resolver)

    payload = asyncio.run(tools.search_google_scholar("traffic flow"))

    assert payload["success"] is False
    assert "key/with space" not in payload["error"]
    assert "key%2Fwith+space" not in payload["error"]
