# Google Scholar through SerpAPI

## Status

This provider is experimental and optional. It queries Google Scholar **through SerpAPI**. It is not direct scraping and is not an official Google Scholar API.

A `SERPAPI_API_KEY` and an active SerpAPI account or allowance are required. Review the official [SerpAPI Google Scholar documentation](https://serpapi.com/google-scholar-api) for current pricing, quotas, and fields.

## Configuration

```bash
academic-research configure --provider google-scholar
academic-research status
```

The wizard uses hidden input and protected local storage. Environment variables remain supported and take precedence.

## Example

```bash
academic-research search "traffic flow low visibility" \
  --sources google_scholar --limit 10 --year 2020-2026
```

The provider supports pagination, language, year bounds, and date sorting through its provider-specific Python or MCP method.

## Metadata caution

Google Scholar organic results often provide a snippet rather than a publisher abstract. Academic Research Tools stores that text under `metadata.snippet` and leaves the normalized `abstract` field empty. This prevents an agent from presenting a search snippet as a verified abstract.

Citation links and versions reported by SerpAPI remain provider-specific metadata. Verify bibliographic data against the publication or another authoritative index before citation.

## Terms

Users are responsible for complying with SerpAPI terms and any applicable Google terms. API results and third-party content are not relicensed under this project's MIT license.

This integration is independent and is not affiliated with or endorsed by Google or SerpAPI.
