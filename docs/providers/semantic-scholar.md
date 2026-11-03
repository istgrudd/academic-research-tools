# Semantic Scholar provider

## Access

The provider uses the official Semantic Scholar Academic Graph API at `https://api.semanticscholar.org/graph/v1`.

`SEMANTIC_SCHOLAR_API_KEY` is optional. Without it, requests use shared public capacity and may receive `429 Too Many Requests`. A key can provide a dedicated quota subject to Semantic Scholar's current policies.

Obtain and manage access through the official [Semantic Scholar API documentation](https://www.semanticscholar.org/product/api).

## Configuration

```bash
academic-research configure --provider semantic-scholar
academic-research status
```

The wizard uses hidden input and protected local storage. Environment variables remain supported and take precedence. The value is sent in the `x-api-key` request header and is never returned by status or diagnostics.

## Example

```bash
academic-research search "multi object tracking traffic" \
  --sources semantic_scholar --limit 10 --year 2020-2026
```

## Normalization

The shared paper model preserves Semantic Scholar's paper ID and available DOI, arXiv, Corpus, PubMed, and other external identifiers. Provider-specific fields such as influential citation count, open-access PDF status, publication types, and journal metadata remain under `metadata` with provenance.

## Rate limits and content rights

Timeouts, connection failures, `429`, and `5xx` responses are retried up to two times with 1 s and 2 s backoff. Other `4xx` responses are not retried. If the request still fails, it is reported as a provider failure, and unified search still returns results from successful sources. For a persistent `429`, retry later or configure a key rather than running an aggressive retry loop.

## Timeouts and network reachability

Requests use `ACADEMIC_RESEARCH_TIMEOUT` (default 30 seconds, clamped to 1–120). Some networks block or silently drop traffic to `api.semanticscholar.org`, which on Windows appears as `WinError 10060`. After the retries, the error states that the host could not be reached from this network and suggests checking firewall, ISP, or VPN restrictions, or setting `HTTPS_PROXY`. Proxy settings from the environment and the operating system are honoured through Python's `urllib`.

Run `academic-research doctor --online` to send one request with a 10-second timeout and see whether Semantic Scholar is reachable. With shared public capacity, that check may report `429` even when the network is fine.

Semantic Scholar aggregates content from third parties. The API's availability does not imply that every abstract or metadata field has the same license. Users must follow the API license and any rights attached to underlying content.
