# Semantic Scholar provider

## Access

The provider uses the official Semantic Scholar Academic Graph API at `https://api.semanticscholar.org/graph/v1`.

`SEMANTIC_SCHOLAR_API_KEY` is optional. Without it, requests use shared public capacity and may receive `429 Too Many Requests`. A key can provide a dedicated quota subject to Semantic Scholar's current policies.

Obtain and manage access through the official [Semantic Scholar API documentation](https://www.semanticscholar.org/product/api).

## Configuration

```bash
export SEMANTIC_SCHOLAR_API_KEY="your-key"
academic-research status
```

The value is sent in the `x-api-key` request header and is never returned by `status`.

## Example

```bash
academic-research search "multi object tracking traffic" \
  --sources semantic_scholar --limit 10 --year 2020-2026
```

## Normalization

The shared paper model preserves Semantic Scholar's paper ID and available DOI, arXiv, Corpus, PubMed, and other external identifiers. Provider-specific fields such as influential citation count, open-access PDF status, publication types, and journal metadata remain under `metadata` with provenance.

## Rate limits and content rights

A `429` response is reported as a provider failure; unified search still returns results from successful sources. Retry later or configure a key rather than running an aggressive retry loop.

Semantic Scholar aggregates content from third parties. The API's availability does not imply that every abstract or metadata field has the same license. Users must follow the API license and any rights attached to underlying content.
