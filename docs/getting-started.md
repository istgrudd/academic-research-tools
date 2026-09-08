# Getting started

## Requirements

- Python 3.10 or newer
- internet access to the provider endpoint you use
- credentials only for the providers that require them

## Install from source

```bash
git clone https://github.com/istgrudd/academic-research-tools.git
cd academic-research-tools
python -m venv .venv
. .venv/bin/activate
python -m pip install .
```

After the first PyPI release, `pip install academic-research-tools` and `pipx install academic-research-tools` provide the same CLI.

Verify the installation:

```bash
academic-research --version
academic-research status
```

## First search without credentials

```bash
academic-research search "traffic flow estimation low visibility" \
  --sources arxiv semantic_scholar \
  --limit 5
```

CLI search output is JSON so it can be piped to `jq`, saved, or consumed by another program. If one source fails, the `errors` object records that failure while successful results remain available.

Available source identifiers are:

- `arxiv`
- `semantic_scholar`
- `scopus`
- `google_scholar`

`google_scholar` means Google Scholar discovery through SerpAPI.

## Configure optional providers

Export only the credentials you need. For example:

```bash
export SEMANTIC_SCHOLAR_API_KEY="..."
export ELSEVIER_API_KEY="..."
```

Then verify booleans, not secret values:

```bash
academic-research status --json
```

Read [Credential setup](credentials.md) before storing keys.

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

## Start the MCP server

```bash
academic-research serve
```

The process communicates over standard input/output. Configure your MCP host to start it; do not run it as a public HTTP service. See [MCP integration](integrations/generic-mcp.md).

## Understand result quality

Every normalized paper keeps its provider and source IDs. Unified search merges only high-confidence duplicates and records contributing sources in provenance. Review provider terms and the underlying record before using metadata in a publication, systematic review, or citation list.
