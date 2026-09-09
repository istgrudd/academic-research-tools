# Academic Research Tools

Evidence-grounded academic literature discovery for AI agents, MCP clients, command-line workflows, and Python applications.

[![CI](https://github.com/istgrudd/academic-research-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/istgrudd/academic-research-tools/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Academic Research Tools provides one normalized interface over several literature sources while preserving the source and identifiers of every record. Its core is independent of any agent harness; MCP, CLI, Python, and Hermes are adapters over the same implementation.

## Providers

| Provider | Credential | Availability | Notes |
|---|---|---|---|
| arXiv | None | Core | Official public Atom API |
| Semantic Scholar | Optional `SEMANTIC_SCHOLAR_API_KEY` | Core | Unauthenticated access uses shared public quota |
| Scopus | `ELSEVIER_API_KEY` | Core, optional at runtime | Metadata and abstracts may require subscription or institutional IP |
| Google Scholar through SerpAPI | `SERPAPI_API_KEY` | Experimental | Third-party SerpAPI integration; not direct scraping or an official Google Scholar API |

The package remains useful without credentials: arXiv is available immediately and Semantic Scholar can be queried without a key, subject to public rate limits.

## Features

- Normalized `Paper`, `Author`, `SearchResult`, and `UnifiedSearchResult` contracts
- Concurrent multi-provider search with partial-failure reporting
- Conservative deduplication by DOI, base arXiv ID, or normalized title plus year
- Per-record provenance and provider identifiers
- Local stdio MCP server for compatible clients
- Automation-friendly CLI and direct Python API
- Thin native Hermes Agent adapter
- Protected local credential configuration with environment overrides
- Interactive hidden-input credential wizard and offline diagnostics
- One-command Claude Code and Codex MCP plus skill installation
- Progressive onboarding that never blocks the first keyless search
- No telemetry

## Installation

### From GitHub

```bash
git clone https://github.com/istgrudd/academic-research-tools.git
cd academic-research-tools
python -m venv .venv
. .venv/bin/activate
python -m pip install .
```

### From PyPI

```bash
pip install academic-research-tools
# or
pipx install academic-research-tools
```

No credential is required to verify the installation:

```bash
academic-research --version
academic-research doctor
academic-research status
academic-research search "traffic flow estimation low visibility" \
  --sources arxiv,semantic_scholar --limit 5
```

Configure optional providers later, only when you need them:

```bash
academic-research configure
```

Secret input is hidden. Do not paste API keys into chat or pass them as command arguments.

Install the MCP server and workflow skill for a coding agent:

```bash
academic-research install --platform claude-code
# or
academic-research install --platform codex
```

The installer does not launch credential configuration. arXiv and Semantic Scholar public access remain ready for immediate use.

See [Getting started](docs/getting-started.md) and [Credential setup](docs/credentials.md).

## MCP quick start

Run the local stdio server:

```bash
academic-research serve
```

If you use `uvx` without a prior install, configure the MCP client to execute:

```bash
uvx --from academic-research-tools academic-research serve
```

Generic MCP configuration:

```json
{
  "mcpServers": {
    "academic-research": {
      "command": "uvx",
      "args": [
        "--from",
        "academic-research-tools",
        "academic-research",
        "serve"
      ],
      "env": {
        "SEMANTIC_SCHOLAR_API_KEY": "${SEMANTIC_SCHOLAR_API_KEY}",
        "ELSEVIER_API_KEY": "${ELSEVIER_API_KEY}"
      }
    }
  }
}
```

Only include environment variables for providers you intend to use. The protected user configuration is also read automatically. Details: [generic MCP](docs/integrations/generic-mcp.md), [Claude Code](docs/integrations/claude-code.md), [Codex](docs/integrations/codex.md), [Claude Desktop](docs/integrations/claude-desktop.md), and [Cursor](docs/integrations/cursor.md).

### MCP tools

- `research_provider_status`
- `search_papers`
- `search_arxiv`
- `search_semantic_scholar`
- `search_scopus`
- `get_scopus_abstract`
- `search_scopus_authors`
- `search_google_scholar`

## Python API

```python
from academic_research import ResearchService

client = ResearchService.from_environment()
result = client.search(
    "traffic flow estimation under low visibility",
    sources=["arxiv", "semantic_scholar", "scopus"],
    limit_per_source=10,
    year="2020-2026",
)

for paper in result.papers:
    print(paper.title, paper.doi, paper.provenance)

if result.errors:
    print("Partial provider failures:", result.errors)
```

A provider that is not configured is excluded from `ResearchService.from_environment()`. The MCP unified search preserves results from available providers and reports missing optional providers with a configuration command. A provider-specific request returns an actionable error rather than silently substituting a different source.

## Hermes Agent

Current Hermes installations can install the repository directly:

```bash
hermes plugins install istgrudd/academic-research-tools --enable
```

Pip-distributed discovery is also declared through the `hermes_agent.plugins` entry-point group. Scopus and SerpAPI use per-tool checks, so missing optional credentials never disable arXiv or Semantic Scholar.

See [Hermes integration](docs/integrations/hermes.md).

## Credential safety

Credentials are resolved from environment variables first and a protected per-user JSON file second. The interactive wizard writes mode `0700` directories and mode `0600` files on Unix. The local file is plaintext and is not an encrypted vault.

This project does not:

- accept secrets as command-line arguments
- print credential values in `status`
- request credentials through an agent conversation
- display credential values in diagnostics or provider status
- store API responses automatically
- send telemetry
- require all providers to be configured

Do not commit `.env`; it is ignored by Git. See [SECURITY.md](SECURITY.md).

## Development

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
ruff check src tests __init__.py
pytest
python -m build
```

Tests use synthetic fixtures and do not spend provider quota. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Scope and limitations

- Search ranking and coverage differ by provider.
- Citation counts from different providers are retained with provenance and should not be treated as directly interchangeable.
- Deduplication is intentionally conservative; ambiguous records may remain separate.
- This project does not bypass paywalls or grant access beyond the user's provider entitlement.
- Remote hosted MCP, operating-system keyring integration, and automatic literature-review decisions are outside the v0.2 scope.

## Legal and data-provider notice

This project is an independent, unofficial integration and is not affiliated with or endorsed by Elsevier, Scopus, Semantic Scholar, arXiv, Google, or SerpAPI. Users are responsible for complying with each provider's API terms, acceptable-use policies, subscription conditions, and data licenses. The MIT license covers this project's source code, not provider data or services.

Thank you to arXiv for use of its open access interoperability.

## License

Source code is available under the [MIT License](LICENSE).
