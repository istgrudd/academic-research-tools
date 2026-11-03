import json

import pytest

from academic_research.cli import main
from academic_research.credentials import CredentialResolver
from academic_research.doctor import doctor_report, online_providers
from academic_research.models import SearchResult
from academic_research.providers.arxiv import ArxivProvider
from academic_research.providers.scopus import ScopusProvider
from academic_research.providers.semantic_scholar import (
    SemanticScholarAPIError,
    SemanticScholarProvider,
)

SECRETS = {
    "SEMANTIC_SCHOLAR_API_KEY": "s2-secret-value-123",
    "ELSEVIER_API_KEY": "elsevier-secret-value-456",
}


class ProbeProvider:
    def __init__(self, source, error=None):
        self.source = source
        self.error = error
        self.calls = []

    def search(self, query, **kwargs):
        self.calls.append({"query": query, **kwargs})
        if self.error:
            raise self.error
        return SearchResult(source=self.source, query=query, papers=[], total=1)


class ExplodingProvider:
    def search(self, *args, **kwargs):
        raise AssertionError("offline doctor must not contact providers")


def _resolver(tmp_path, environ=None):
    return CredentialResolver(config_path=tmp_path / "credentials.json", environ=environ or {})


def test_doctor_without_online_flag_makes_no_requests(tmp_path):
    report = doctor_report(
        resolver=_resolver(tmp_path),
        online_providers_factory=lambda resolver: {"arxiv": ExplodingProvider()},
    )

    assert report["success"] is True
    assert "online" not in report


def test_doctor_online_reports_each_active_provider(tmp_path):
    arxiv = ProbeProvider("arxiv")
    s2 = ProbeProvider(
        "semantic_scholar",
        error=SemanticScholarAPIError("Network error while calling Semantic Scholar API"),
    )

    report = doctor_report(
        resolver=_resolver(tmp_path),
        online=True,
        online_providers_factory=lambda resolver: {"arxiv": arxiv, "semantic_scholar": s2},
    )

    online = report["online"]
    assert online["timeout_seconds"] == 10
    assert online["all_reachable"] is False
    assert online["providers"]["arxiv"]["reachable"] is True
    assert online["providers"]["arxiv"]["error"] is None
    assert isinstance(online["providers"]["arxiv"]["elapsed_ms"], int)
    assert online["providers"]["semantic_scholar"]["reachable"] is False
    assert "SemanticScholarAPIError" in online["providers"]["semantic_scholar"]["error"]
    assert report["success"] is False
    assert len(arxiv.calls) == 1
    assert arxiv.calls[0]["limit"] == 1
    assert len(s2.calls) == 1


def test_doctor_online_success_requires_every_check_to_pass(tmp_path):
    report = doctor_report(
        resolver=_resolver(tmp_path),
        online=True,
        online_providers_factory=lambda resolver: {"arxiv": ProbeProvider("arxiv")},
    )

    assert report["online"]["all_reachable"] is True
    assert report["success"] is True


def test_doctor_online_report_never_contains_credential_values(tmp_path):
    leaking = ProbeProvider(
        "scopus",
        error=RuntimeError(f"echoed key {SECRETS['ELSEVIER_API_KEY']} in provider error"),
    )

    report = doctor_report(
        resolver=_resolver(tmp_path, SECRETS),
        online=True,
        online_providers_factory=lambda resolver: {
            "semantic_scholar": ProbeProvider("semantic_scholar"),
            "scopus": leaking,
        },
    )

    serialized = json.dumps(report)
    for secret in SECRETS.values():
        assert secret not in serialized
    assert "[REDACTED]" in report["online"]["providers"]["scopus"]["error"]


def test_online_providers_use_ten_second_timeout_single_request_and_active_set(tmp_path):
    providers = online_providers(_resolver(tmp_path))

    assert set(providers) == {"arxiv", "semantic_scholar"}
    assert isinstance(providers["arxiv"], ArxivProvider)
    for provider in providers.values():
        assert provider.timeout == 10.0
        assert provider.max_retries == 0

    configured = online_providers(_resolver(tmp_path, SECRETS))
    assert isinstance(configured["semantic_scholar"], SemanticScholarProvider)
    assert isinstance(configured["scopus"], ScopusProvider)
    assert configured["scopus"].timeout == 10.0
    assert "google_scholar" not in configured


@pytest.fixture
def cli_online(monkeypatch, tmp_path):
    resolver = _resolver(tmp_path, SECRETS)
    monkeypatch.setattr("academic_research.cli.CredentialResolver", lambda: resolver)

    def install(providers):
        monkeypatch.setattr(
            "academic_research.doctor.online_providers", lambda resolver: providers
        )

    return install


def test_cli_doctor_online_prints_marks_and_reasons_without_secrets(cli_online, capsys):
    cli_online(
        {
            "arxiv": ProbeProvider("arxiv"),
            "semantic_scholar": ProbeProvider(
                "semantic_scholar",
                error=SemanticScholarAPIError(
                    f"timed out using {SECRETS['SEMANTIC_SCHOLAR_API_KEY']}"
                ),
            ),
        }
    )

    assert main(["doctor", "--online"]) == 1

    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    assert any(line.startswith("✓ arxiv") for line in lines)
    assert any(line.startswith("✗ semantic_scholar") and "timed out" in line for line in lines)
    for secret in SECRETS.values():
        assert secret not in captured.out
        assert secret not in captured.err


def test_cli_doctor_online_json_includes_online_section(cli_online, capsys):
    cli_online({"arxiv": ProbeProvider("arxiv")})

    assert main(["doctor", "--online", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["online"]["providers"]["arxiv"]["reachable"] is True
    assert payload["ready_for_search"] is True
    for secret in SECRETS.values():
        assert secret not in json.dumps(payload)


def test_cli_doctor_without_online_stays_offline(cli_online, capsys):
    cli_online({"arxiv": ExplodingProvider()})

    assert main(["doctor", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "online" not in payload
