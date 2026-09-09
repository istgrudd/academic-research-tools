import json

from academic_research.cli import main
from academic_research.credentials import CredentialResolver
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


def test_configure_scopus_uses_hidden_prompt_and_never_prints_secret(
    monkeypatch, capsys, tmp_path
):
    resolver = CredentialResolver(config_path=tmp_path / "credentials.json", environ={})
    monkeypatch.setattr("academic_research.cli.CredentialResolver", lambda: resolver)
    monkeypatch.setattr(
        "academic_research.cli._read_secret", lambda prompt: "interactive-secret"
    )

    assert main(["configure", "--provider", "scopus"]) == 0

    captured = capsys.readouterr()
    assert resolver.get("ELSEVIER_API_KEY") == "interactive-secret"
    assert "interactive-secret" not in captured.out
    assert "interactive-secret" not in captured.err
    assert "Scopus" in captured.out


def test_configure_remove_deletes_only_selected_saved_credential(
    monkeypatch, capsys, tmp_path
):
    resolver = CredentialResolver(config_path=tmp_path / "credentials.json", environ={})
    resolver.set("ELSEVIER_API_KEY", "saved-secret")
    resolver.set("SERPAPI_API_KEY", "other-secret")
    monkeypatch.setattr("academic_research.cli.CredentialResolver", lambda: resolver)

    assert main(["configure", "--remove", "scopus"]) == 0

    assert resolver.get("ELSEVIER_API_KEY") is None
    assert resolver.get("SERPAPI_API_KEY") == "other-secret"
    assert "saved-secret" not in capsys.readouterr().out


def test_configure_without_provider_shows_menu_and_prompts(monkeypatch, capsys, tmp_path):
    resolver = CredentialResolver(config_path=tmp_path / "credentials.json", environ={})
    monkeypatch.setattr("academic_research.cli.CredentialResolver", lambda: resolver)
    monkeypatch.setattr("builtins.input", lambda prompt: "1")
    monkeypatch.setattr("academic_research.cli._read_secret", lambda prompt: "menu-secret")

    assert main(["configure"]) == 0

    assert resolver.get("ELSEVIER_API_KEY") == "menu-secret"
    output = capsys.readouterr().out
    assert "Scopus / Elsevier" in output
    assert "menu-secret" not in output


def test_install_command_reports_optional_configuration_without_prompting(
    monkeypatch, capsys
):
    calls = []

    def fake_install(platform):
        calls.append(platform)
        return {
            "platform": platform,
            "configured": True,
            "server": "academic-research",
            "launcher": ["academic-research", "serve"],
            "skill_path": "/tmp/SKILL.md",
            "credentials_requested": False,
        }

    monkeypatch.setattr("academic_research.cli.install_platform", fake_install)

    assert main(["install", "--platform", "codex"]) == 0

    output = capsys.readouterr().out
    assert calls == ["codex"]
    assert "Ready now" in output
    assert "arXiv" in output
    assert "Optionally" in output
    assert "academic-research configure" in output


def test_doctor_json_returns_success_when_optional_credentials_are_missing(
    monkeypatch, capsys, tmp_path
):
    resolver = CredentialResolver(config_path=tmp_path / "credentials.json", environ={})
    monkeypatch.setattr("academic_research.cli.CredentialResolver", lambda: resolver)

    assert main(["doctor", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["success"] is True
    assert payload["ready_for_search"] is True
    assert payload["onboarding"]["configuration_required"] is False


def test_forbidden_secret_argument_is_rejected_without_echoing_value(capsys):
    assert main(
        ["configure", "--provider", "scopus", "--api-key", "argument-secret"]
    ) == 2

    captured = capsys.readouterr()
    assert "argument-secret" not in captured.out
    assert "argument-secret" not in captured.err
    assert "interactive terminal" in captured.err

    for option in (
        "--elsevier-api-key=embedded-secret",
        "--apikey=embedded-secret",
        "--apiKey=embedded-secret",
    ):
        assert main(
            ["configure", "--provider", "scopus", option]
        ) == 2
        captured = capsys.readouterr()
        assert "embedded-secret" not in captured.out
        assert "embedded-secret" not in captured.err
