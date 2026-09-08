import json

from academic_research.cli import main
from academic_research.models import Paper, UnifiedSearchResult


class StubService:
    def __init__(self):
        self.calls = []

    def search(self, query, **kwargs):
        self.calls.append({"query": query, **kwargs})
        return UnifiedSearchResult(
            query=query,
            sources_requested=kwargs.get("sources") or ["arxiv"],
            sources_succeeded=["arxiv"],
            sources_failed=[],
            retrieved_count=1,
            deduplicated_count=1,
            papers=[Paper(id="arxiv:1", title="Paper", source="arxiv")],
        )


def test_status_json_never_prints_secret(monkeypatch, capsys):
    monkeypatch.setenv("ELSEVIER_API_KEY", "super-secret-value")

    assert main(["status", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["scopus"]["available"] is True
    assert "super-secret-value" not in json.dumps(payload)


def test_search_cli_parses_sources_and_emits_json(monkeypatch, capsys):
    service = StubService()
    monkeypatch.setattr(
        "academic_research.cli.ResearchService.from_environment",
        lambda: service,
    )

    assert (
        main(
            [
                "search",
                "academic agents",
                "--sources",
                "arxiv,semantic_scholar",
                "--limit",
                "4",
                "--year",
                "2024-2026",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["success"] is True
    assert payload["deduplicated_count"] == 1
    assert service.calls == [
        {
            "query": "academic agents",
            "sources": ["arxiv", "semantic_scholar"],
            "limit_per_source": 4,
            "year": "2024-2026",
        }
    ]


def test_search_cli_returns_nonzero_for_invalid_source(monkeypatch, capsys):
    class FailingService:
        def search(self, *args, **kwargs):
            raise ValueError("Unknown or unavailable source: pubmed")

    monkeypatch.setattr(
        "academic_research.cli.ResearchService.from_environment",
        lambda: FailingService(),
    )

    assert main(["search", "test", "--sources", "pubmed"]) == 2
    assert "Unknown or unavailable source" in capsys.readouterr().err


def test_serve_delegates_to_mcp_entrypoint(monkeypatch):
    called = []
    monkeypatch.setattr("academic_research.cli.run_mcp", lambda: called.append(True))

    assert main(["serve"]) == 0
    assert called == [True]
