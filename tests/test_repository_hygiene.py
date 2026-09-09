from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_public_repository_files_are_complete():
    required = [
        "LICENSE",
        "MANIFEST.in",
        "README.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CHANGELOG.md",
        ".env.example",
        ".github/workflows/ci.yml",
        ".github/workflows/publish.yml",
        ".github/workflows/release.yml",
        "docs/getting-started.md",
        "docs/credentials.md",
        "docs/providers/arxiv.md",
        "docs/providers/semantic-scholar.md",
        "docs/providers/scopus.md",
        "docs/providers/google-scholar-serpapi.md",
        "docs/integrations/generic-mcp.md",
        "docs/integrations/hermes.md",
        "docs/integrations/claude-code.md",
        "docs/integrations/codex.md",
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


def test_release_versions_and_progressive_onboarding_are_synchronized():
    metadata = (ROOT / "pyproject.toml").read_text()
    package = (ROOT / "src/academic_research/__init__.py").read_text()
    manifest = (ROOT / "plugin.yaml").read_text()
    skill = (
        ROOT
        / "src/academic_research/skills/academic-research-workflow/SKILL.md"
    ).read_text()

    assert 'version = "0.2.0"' in metadata
    assert '__version__ = "0.2.0"' in package
    assert "version: 0.2.0" in manifest
    assert "version: 0.2.0" in skill
    assert "Do not require it for the first search" in skill


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


def test_release_automation_preserves_a_manual_immutable_version_gate():
    release = (ROOT / ".github/workflows/release.yml").read_text()
    publish = (ROOT / ".github/workflows/publish.yml").read_text()

    assert "workflow_dispatch:" in release
    assert "version:" in release
    assert "refs/heads/main" in release
    assert "contents: write" in release
    assert "git tag -a" in release
    assert "gh release create" in release
    assert "--verify-tag" in release
    assert "gh workflow run publish.yml" in release
    assert "Smoke-test built wheel and MCP stdio" in release
    assert "stdio_client" in release
    assert "release:" not in release.split("workflow_dispatch:", 1)[0]
    assert "default: v0.1.0" not in publish
    assert "id-token: write" in publish
