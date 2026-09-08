# Architecture

Academic Research Tools separates data access from agent integration.

```text
Claude · Hermes · Cursor · other MCP hosts · CLI · Python
                         │
                 adapters / MCP
                         │
       validation · normalization · deduplication
                         │
       arXiv · Semantic Scholar · Scopus · SerpAPI
```

## Core

`src/academic_research/` contains provider-neutral contracts and orchestration:

- `models.py`: JSON-safe normalized records
- `service.py`: provider selection, concurrent searches, partial failures, and conservative deduplication
- `status.py`: credential-safe availability booleans
- `providers/`: official or explicitly documented third-party API clients

Core provider code has no dependency on Hermes or another agent harness.

## Adapters

- `mcp_server.py` exposes local stdio tools through the official MCP SDK.
- `cli.py` offers status, search, and serve commands.
- `hermes_plugin.py` registers native Hermes tools and delegates to the same facade.

## Failure model

Provider failures are isolated. Unified search returns successful records plus an `errors` mapping and warnings. A caller can decide whether partial evidence is acceptable.

## Deduplication

Records merge in this order:

1. normalized DOI
2. base arXiv ID
3. normalized title plus publication year

The merge retains source IDs, contributing providers, provider-specific metadata, and citation-count provenance. It prefers a non-empty or richer abstract but does not infer missing claims.

## Credential boundary

Provider keys enter only through process environment variables. Local stdio MCP avoids a hosted credential-custody service. Remote MCP transport and persistent secret storage are intentionally outside v0.1.
