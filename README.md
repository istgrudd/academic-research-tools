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
- Local-first credentials with no telemetry

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

After the first package release:

```bash
pip install academic-research-tools
# or
pipx install academic-research-tools
```

No credential is required to verify the installation:

```bash
academic-research --version
academic-research status
academic-research search "traffic flow estimation low visibility" \
  --sources arxiv semantic_scholar --limit 5
```

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

Only include environment variables for providers you intend to use. Details: [generic MCP](docs/integrations/generic-mcp.md), [Claude Desktop](docs/integrations/claude-desktop.md), and [Cursor](docs/integrations/cursor.md).

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

A provider that is not configured is excluded from `ResearchService.from_environment()`. Explicitly requesting a missing provider returns an actionable error rather than silently changing the requested source list.

## Hermes Agent

Current Hermes installations can install the repository directly:

```bash
hermes plugins install istgrudd/academic-research-tools --enable
```

Pip-distributed discovery is also declared through the `hermes_agent.plugins` entry-point group. Scopus and SerpAPI use per-tool checks, so missing optional credentials never disable arXiv or Semantic Scholar.

See [Hermes integration](docs/integrations/hermes.md).

## Credential safety

Credentials are read only from environment variables. This project does not:

- accept secrets as command-line arguments
- print credential values in `status`
- store credentials or API responses automatically
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
- Remote hosted MCP, long-term credential storage, and automatic literature-review decisions are outside the v0.1 scope.

## Legal and data-provider notice

This project is an independent, unofficial integration and is not affiliated with or endorsed by Elsevier, Scopus, Semantic Scholar, arXiv, Google, or SerpAPI. Users are responsible for complying with each provider's API terms, acceptable-use policies, subscription conditions, and data licenses. The MIT license covers this project's source code, not provider data or services.

Thank you to arXiv for use of its open access interoperability.

## License

Source code is available under the [MIT License](LICENSE).
