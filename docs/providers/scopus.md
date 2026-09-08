# Scopus provider

## Access

The provider uses official Elsevier APIs for:

- Scopus Search
- Abstract Retrieval
- Author Search

An `ELSEVIER_API_KEY` is required for these tools. An API key alone does not guarantee access to every endpoint or field. Abstracts, complete views, author data, and some metadata may depend on an Elsevier subscription, institutional entitlement, or the institution's recognized IP range.

Obtain and manage a key through the official [Elsevier Developer Portal](https://dev.elsevier.com/).

## Configuration

```bash
export ELSEVIER_API_KEY="your-key"
# Only if issued by an eligible institution:
export ELSEVIER_INST_TOKEN="your-institution-token"
academic-research status
```

The API key is sent in `X-ELS-APIKey`. The optional institutional token is sent in `X-ELS-Insttoken`. Neither value is printed or persisted by this package.

## Search syntax

Scopus uses its own query syntax. Examples:

```text
TITLE-ABS-KEY("traffic flow" AND "low visibility")
DOI(10.1000/example)
AUTHLASTNAME(Smith) AND AUTHFIRST(John)
```

CLI unified search passes the query to Scopus:

```bash
academic-research search 'TITLE-ABS-KEY("vehicle detection")' \
  --sources scopus --limit 10
```

For Scopus-specific pagination, sorting, views, fields, and facets, use the MCP `search_scopus` tool or the Python `ScopusProvider` API.

## Abstract retrieval identifiers

`get_scopus_abstract` accepts DOI, EID, Scopus ID, PII, PubMed ID, and PUI. `identifier_type="auto"` recognizes common DOI, EID, and numeric Scopus ID forms. Set the type explicitly if an identifier is ambiguous.

## Quota and provenance

Elsevier rate-limit headers are returned as structured quota metadata when available. Search and detail results preserve EID, DOI, PII, PubMed ID, Scopus ID, links, and source endpoint provenance.

## Terms and redistribution

Do not commit or redistribute large API responses, licensed abstracts, or bulk Scopus datasets with this project. The MIT license applies only to the client source code. Users must comply with Elsevier API terms, subscription conditions, and data licenses.

“Scopus” and “Elsevier” are used descriptively. This is an independent integration and is not affiliated with or endorsed by Elsevier or Scopus.
