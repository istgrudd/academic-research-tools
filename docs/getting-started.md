# Getting started

## Requirements

- Python 3.10 or newer
- internet access to the provider endpoint you use
- credentials only for providers that require them

## Install from PyPI

```bash
pip install academic-research-tools
# or
pipx install academic-research-tools
```

Install from source for development:

```bash
git clone https://github.com/istgrudd/academic-research-tools.git
cd academic-research-tools
python -m venv .venv
. .venv/bin/activate
python -m pip install .
```

Verify the installation without adding credentials:

```bash
academic-research --version
academic-research doctor
academic-research status
```

## First search without credentials

```bash
academic-research search "traffic flow estimation low visibility" \
  --sources arxiv,semantic_scholar \
  --limit 5
```

CLI search output is JSON so it can be piped to `jq`, saved, or consumed by another program. If one source fails, the `errors` object records that failure while successful results remain available.

Available source identifiers are:

- `arxiv`
- `semantic_scholar`
- `scopus`
- `google_scholar`

`google_scholar` means Google Scholar discovery through SerpAPI.

## Optional provider configuration

Do not configure credentials merely to prove the package works. When you want Scopus, Google Scholar through SerpAPI, or dedicated Semantic Scholar quota, run:

```bash
academic-research configure
```

The wizard uses hidden terminal input and stores the selected credential in a protected user configuration file. Environment variables remain supported and take precedence.

Useful commands:

```bash
academic-research configure --list
academic-research configure --remove scopus
academic-research doctor --json
```

Read [Credential setup](credentials.md) before storing keys. Never paste an API key into an AI chat or pass it as a command argument.

## Claude Code and Codex

Register both the MCP server and bundled workflow skill with one command:

```bash
academic-research install --platform claude-code
# or
academic-research install --platform codex
```

Installation is non-interactive with respect to credentials. It does not run `academic-research configure`. arXiv and Semantic Scholar public access are ready for immediate use.

See [Claude Code integration](integrations/claude-code.md) and [Codex integration](integrations/codex.md).

## Use the Python API

```python
from academic_research import ResearchService

service = ResearchService.from_environment()
result = service.search(
    "low visibility vehicle tracking",
    sources=["arxiv", "semantic_scholar"],
    limit_per_source=10,
)

print(result.retrieved_count, result.deduplicated_count)
for paper in result.papers:
    print(paper.title, paper.source_ids)
```

`ResearchService.from_environment()` resolves environment variables first and the protected user configuration second. Recreate the service instance after changing credentials in a long-running Python process. The MCP adapter reloads credentials for each tool call automatically.

## Start the MCP server

```bash
academic-research serve
```

The process communicates over standard input/output. Configure your MCP host to start it; do not run it as a public HTTP service. See [MCP integration](integrations/generic-mcp.md).

## Understand result quality

Every normalized paper keeps its provider and source IDs. Unified search merges only high-confidence duplicates and records contributing sources in provenance. Review provider terms and the underlying record before using metadata in a publication, systematic review, or citation list.
