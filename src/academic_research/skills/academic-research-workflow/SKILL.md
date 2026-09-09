---
name: academic-research-workflow
description: Use when setting up or using Academic Research Tools for auditable multi-source literature discovery.
version: 0.2.0
---

# Academic research workflow

Use Academic Research Tools for evidence-grounded literature discovery with the least possible setup friction.

## Progressive onboarding

Treat credentials as optional capability upgrades, not as an installation gate.

When the user asks to set up the tools and search for papers:

1. Install the package and register the MCP integration.
2. Call `research_provider_status` or `academic-research status --json`.
3. If any provider is available, perform the requested search immediately.
4. Mention `academic-research configure` once as an optional next step after setup. Do not require it for the first search.
5. Require configuration only when the user explicitly requests a provider whose required credential is missing.
6. When that provider is unavailable, offer an immediate search through available providers as a fallback.
7. If the host must reconnect before discovering newly registered MCP tools, use the CLI for the first search rather than blocking the user.

A setup-and-search request is complete only after installation, registration, provider detection, a search attempt, and returned results or a concrete provider error. Installation alone is not completion.

Use non-coercive wording such as:

```text
Academic Research Tools is installed and ready with arXiv and Semantic Scholar.
I will search those sources now. Optionally, run `academic-research configure`
later to enable additional providers.
```

Do not automatically launch `academic-research configure` after installation.

## Credential boundary

- Never ask the user to paste an API key, token, or password into chat.
- Never accept credentials through command-line arguments.
- The user enters provider credentials directly in a local interactive terminal with `academic-research configure`; secret input is hidden.
- Never read, display, summarize, log, or commit credential values.
- Use provider status only to report availability, whether a credential is configured, and its source.

## Literature discovery

1. Clarify the research question, context, date range, and inclusion criteria when they materially affect the search.
2. Start with `search_papers` across available sources for broad discovery.
3. Use provider-specific search when query syntax or metadata needs differ.
4. Deduplicate by DOI first, then title and year. Preserve all provider identifiers.
5. Use `get_scopus_abstract` only for plausible candidates to conserve quota.
6. Treat Google Scholar snippets as snippets, never as full abstracts.
7. Label candidates `include`, `maybe`, or `exclude` with evidence-based reasons.
8. Distinguish unavailable evidence from evidence of irrelevance.
9. Keep citation counts separate by source because they are not directly comparable.
10. Report provider failures, rate limits, and entitlement restrictions.

## Safety and limitations

- Search metadata is not automatically evidence of paper quality.
- arXiv includes preprints that may not be peer reviewed.
- Scopus access depends on the user's Elsevier key and entitlement.
- Semantic Scholar public access may be rate limited.
- Google Scholar support uses optional third-party SerpAPI.
