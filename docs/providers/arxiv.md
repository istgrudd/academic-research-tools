# arXiv provider

## Access

The provider uses the public arXiv API at `https://export.arxiv.org/api/query`. No API key is required.

Supported operations:

- free-text or arXiv query syntax search
- retrieval by one or more arXiv IDs
- relevance, submission-date, or update-date sorting
- pagination up to the API's practical limits

## Example

```bash
academic-research search "computer vision low visibility" \
  --sources arxiv --limit 10
```

The MCP-specific `search_arxiv` tool also accepts `ids`, `start`, `sort_by`, and `sort_order`.

## Normalization

The provider maps Atom entries into the shared `Paper` contract and retains:

- the versioned arXiv ID
- primary and PDF URLs
- categories
- journal reference and comment in metadata
- feed attribution and source endpoint in provenance

Deduplication uses the base arXiv ID without a version suffix when available.

## Responsible use

The client sends a descriptive user agent, bounds page size, applies request timeouts, and spaces live requests. Avoid high-rate loops and cache responsibly within arXiv's guidance. The package does not redistribute arXiv records or full text.

Thank you to arXiv for use of its open access interoperability.

Review the current arXiv API and data-use documentation before production use.
