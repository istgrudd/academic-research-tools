---
name: literature-screening
description: Intent-driven Scopus literature discovery and auditable title/abstract screening.
version: 1.0.0
---

# Intent-driven Scopus literature screening

Use this workflow when the user wants relevant papers rather than a raw keyword dump.

1. Ask for or infer the research question, population/context, methods of interest, date range, and explicit inclusion/exclusion criteria.
2. Translate concepts into synonym groups. Build 2–4 Scopus queries with `TITLE-ABS-KEY(...)`; avoid ambiguous acronyms unless anchored by context.
3. Call `scopus_search` with 10–25 results first. Use WADL-native `date` and `subject_area` filters when appropriate. Inspect false positives before paginating broadly.
4. Refine the query using evidence from irrelevant results. Keep a query log so exclusions are auditable.
5. If `google_scholar_search` is available, run a parallel natural-language/quoted-phrase query to broaden recall beyond Scopus. Google Scholar results come through third-party SerpAPI, snippets are not full abstracts, and Scholar citation counts are not directly comparable to Scopus counts.
6. Deduplicate cross-source results by normalized DOI first, then normalized title + year. Preserve source-specific citation counts separately.
7. Retrieve abstracts for plausible Scopus candidates using `scopus_abstract` and the DOI/EID from search results. If entitlement blocks abstract access, label that limitation; do not silently treat a Scholar snippet as the abstract.
8. Screen each candidate into `include`, `maybe`, or `exclude`. Give a concise reason tied to the user's criteria and quote/paraphrase abstract evidence; never invent evidence when an abstract is unavailable.
9. Report counts at each stage: retrieved per source, deduplicated, included, maybe, excluded. Preserve DOI, Scopus ID, title, year, source, and reason.
10. Treat citation count as influence, not relevance or quality. Do not exclude recent papers merely for low citations.

## Query pattern

```text
TITLE-ABS-KEY(
  (concept_a_synonym_1 OR concept_a_synonym_2)
  AND
  (concept_b_synonym_1 OR concept_b_synonym_2)
)
AND PUBYEAR > 2020
```

Use `DOCTYPE(ar)` or `DOCTYPE(cp)` only when the user's protocol requires it. Keep recall high in retrieval, then recover precision during title/abstract screening.

## Safety and limitations

- Scopus API coverage is metadata/abstract-oriented; it does not guarantee full text.
- `COMPLETE`/`FULL` views may require institutional entitlement, campus/VPN IP, or an `ELSEVIER_INST_TOKEN`.
- Respect quota headers returned by every tool call. Avoid retrieving abstracts for obviously irrelevant titles.
- Clearly distinguish “not relevant” from “insufficient information to judge.”
