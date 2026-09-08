---
name: academic-research-workflow
description: Use when performing auditable multi-source academic literature discovery and screening.
version: 0.1.0
---

# Academic research workflow

Use the academic research tools for evidence-grounded literature discovery.

1. Clarify the research question, context, date range, and inclusion criteria.
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
- Never expose, log, or commit provider credentials.
