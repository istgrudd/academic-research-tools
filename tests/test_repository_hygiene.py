from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_public_repository_files_are_complete():
    required = [
        "LICENSE",
        "README.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CHANGELOG.md",
        ".env.example",
        ".github/workflows/ci.yml",
        "docs/getting-started.md",
        "docs/credentials.md",
        "docs/providers/arxiv.md",
        "docs/providers/semantic-scholar.md",
        "docs/providers/scopus.md",
        "docs/providers/google-scholar-serpapi.md",
        "docs/integrations/generic-mcp.md",
        "docs/integrations/hermes.md",
        "docs/integrations/claude-desktop.md",
        "docs/integrations/cursor.md",
    ]
    missing = [path for path in required if not (ROOT / path).is_file()]
    assert missing == []


def test_release_metadata_has_no_placeholders_or_global_credential_gate():
    metadata = (ROOT / "pyproject.toml").read_text()
    manifest = (ROOT / "plugin.yaml").read_text()
    assert "OWNER" not in metadata
    assert "requires_env:" not in manifest
    assert "github.com/istgrudd/academic-research-tools" in metadata


def test_env_example_contains_names_but_no_secret_values():
    lines = (ROOT / ".env.example").read_text().splitlines()
    assignments = [line for line in lines if line and not line.startswith("#")]
    assert assignments == [
        "SEMANTIC_SCHOLAR_API_KEY=",
        "ELSEVIER_API_KEY=",
        "ELSEVIER_INST_TOKEN=",
        "SERPAPI_API_KEY=",
    ]


def test_readme_contains_legal_and_arxiv_notices():
    readme = (ROOT / "README.md").read_text()
    assert "independent, unofficial integration" in readme
    assert "Thank you to arXiv for use of its open access interoperability." in readme
    assert "Google Scholar through SerpAPI" in readme
