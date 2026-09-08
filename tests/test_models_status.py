import asyncio

from academic_research.models import Author, Paper
from academic_research.status import provider_status


def test_paper_contract_is_json_safe_and_preserves_provenance():
    paper = Paper(
        id="doi:10.1000/example",
        title="Evidence-Grounded Research",
        source="semantic_scholar",
        authors=[Author(name="Rudi Firdaus", author_id="a1")],
        doi="10.1000/EXAMPLE",
        source_ids={"doi": "10.1000/example", "semantic_scholar": "p1"},
        provenance={"provider": "Semantic Scholar Academic Graph API"},
    )

    payload = paper.to_dict()

    assert payload["id"] == "doi:10.1000/example"
    assert payload["authors"] == [
        {
            "name": "Rudi Firdaus",
            "author_id": "a1",
            "affiliation": None,
            "profile_url": None,
        }
    ]
    assert payload["source_ids"]["semantic_scholar"] == "p1"
    assert payload["provenance"]["provider"].startswith("Semantic Scholar")


def test_provider_status_is_free_first_and_never_exposes_secret_values(monkeypatch):
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "semantic-secret-value")
    monkeypatch.setenv("ELSEVIER_API_KEY", "elsevier-secret-value")
    monkeypatch.delenv("ELSEVIER_INST_TOKEN", raising=False)
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)

    status = provider_status()

    assert status["arxiv"] == {
        "available": True,
        "authentication": "not_required",
        "authenticated": False,
    }
    assert status["semantic_scholar"]["available"] is True
    assert status["semantic_scholar"]["authenticated"] is True
    assert status["scopus"]["available"] is True
    assert status["scopus"]["authenticated"] is True
    assert status["scopus"]["institutional_token"] is False
    assert status["google_scholar"]["available"] is False

    rendered = repr(status)
    assert "semantic-secret-value" not in rendered
    assert "elsevier-secret-value" not in rendered


def test_provider_status_reports_optional_configuration(monkeypatch):
    for name in (
        "SEMANTIC_SCHOLAR_API_KEY",
        "ELSEVIER_API_KEY",
        "ELSEVIER_INST_TOKEN",
        "SERPAPI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    status = provider_status()

    assert status["arxiv"]["available"] is True
    assert status["semantic_scholar"]["available"] is True
    assert status["semantic_scholar"]["authenticated"] is False
    assert status["scopus"]["available"] is False
    assert status["google_scholar"]["available"] is False
    assert "ELSEVIER_API_KEY" in status["scopus"]["reason"]


def test_research_tools_exposes_provider_status():
    from academic_research.mcp_server import ResearchTools

    payload = asyncio.run(ResearchTools().provider_status())

    assert payload["success"] is True
    assert payload["providers"]["arxiv"]["available"] is True
