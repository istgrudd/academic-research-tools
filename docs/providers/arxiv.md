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

## Query translation

arXiv does not treat a plain string as "all of these words". Free-text queries are therefore translated into all-terms field queries:

| Input | Sent as `search_query` |
|---|---|
| `vehicle counting YOLO ByteTrack` | `all:vehicle AND all:counting AND all:YOLO AND all:ByteTrack` |
| `"traffic volume" estimation` | `all:"traffic volume" AND all:estimation` |
| `ti:yolo AND abs:traffic` | unchanged |

A query is passed through unchanged when it already uses arXiv syntax: a field prefix such as `ti:`, `abs:`, `au:`, `all:`, `cat:`, `co:`, `jr:`, `rn:`, or `id:`; an upper-case `AND`, `OR`, or `ANDNOT`; or parentheses. Quoted phrases stay one term and empty terms are dropped. ID lookups through `ids` are not affected.

If no paper contains every term, the first page (`start=0`) is retried once with the same terms joined by `OR`. The result then carries a warning, `metadata.query_fallback = "any_term"`, and the query actually sent in `metadata.search_query`. Any-term results can be much less relevant. Use fewer terms or explicit arXiv syntax for precise control. Explicit-syntax queries, single-term queries, and later pages never fall back.

## Timeouts and retries

Requests use `ACADEMIC_RESEARCH_TIMEOUT` (default 30 seconds, clamped to 1–120). Timeouts, connection failures, HTTP 429, and HTTP 5xx are retried up to two times with 1 s and 2 s backoff; other 4xx responses are not retried. The client still waits at least three seconds between live requests. If `export.arxiv.org` cannot be reached, the error suggests checking firewall, ISP, or VPN restrictions, or setting `HTTPS_PROXY`. `academic-research doctor --online` checks reachability with one request.

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
