"""JSON schemas exposed to the Hermes model."""

ARXIV_SEARCH_SCHEMA = {
    "name": "arxiv_search",
    "description": (
        "Search or retrieve papers through the official public arXiv Atom API. Supports arXiv field "
        "syntax such as all:, ti:, au:, abs:, cat:, Boolean operators, or exact arXiv IDs. Returns "
        "versioned IDs, full abstracts, authors, categories, DOI, journal reference, and PDF URLs."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "arXiv API query, e.g. ti:\"vision transformer\" AND cat:cs.CV."},
            "ids": {"type": "array", "items": {"type": "string"}, "description": "Optional exact arXiv IDs, including version suffixes when needed."},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            "start": {"type": "integer", "minimum": 0, "maximum": 30000},
            "sort_by": {"type": "string", "enum": ["relevance", "lastUpdatedDate", "submittedDate"]},
            "sort_order": {"type": "string", "enum": ["ascending", "descending"]},
        },
        "anyOf": [{"required": ["query"]}, {"required": ["ids"]}],
    },
}

SEMANTIC_SCHOLAR_SEARCH_SCHEMA = {
    "name": "semantic_scholar_search",
    "description": (
        "Search the official Semantic Scholar Academic Graph API. Use this free structured alternative "
        "to Google Scholar for broad discovery, abstracts, DOI/arXiv identifiers, citations, references, "
        "fields of study, and open-access PDF links. An API key is optional."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Natural-language or title/author paper query."},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            "offset": {"type": "integer", "minimum": 0, "maximum": 9999},
            "year": {"type": "string", "description": "Optional YYYY or YYYY-YYYY publication-year filter."},
        },
        "required": ["query"],
    },
}

SCOPUS_SEARCH_SCHEMA = {
    "name": "scopus_search",
    "description": (
        "Search the official Scopus index through Elsevier's API. Use Scopus field syntax such as "
        "TITLE-ABS-KEY(...), PUBYEAR, AUTH, AFFIL, DOCTYPE, and Boolean operators. Use this instead "
        "of generic web search when the user needs Scopus-indexed literature, citation counts, DOI, "
        "or auditable title/abstract screening. Start broad, inspect results, then refine the query."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Scopus query, e.g. TITLE-ABS-KEY((resume OR CV) AND recruitment) AND PUBYEAR > 2020"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 25, "description": "Results per page (max 25)."},
            "start": {"type": "integer", "minimum": 0, "maximum": 4999, "description": "Zero-based pagination offset."},
            "sort": {
                "type": "string",
                "description": "Up to 3 comma-separated WADL sort fields with optional +/-: relevancy, citedby-count, coverDate, creator, pubyear, publicationName, volume, etc.",
            },
            "view": {"type": "string", "enum": ["STANDARD", "COMPLETE"], "description": "COMPLETE may require stronger institutional entitlement."},
            "date": {"type": "string", "description": "Official date filter in YYYY or YYYY-YYYY form, e.g. 2020-2026."},
            "subject_area": {
                "type": "string",
                "description": "Scopus subject code, e.g. COMP, ENGI, MEDI, BUSI, SOCI, or MULT.",
            },
            "fields": {"type": "string", "description": "Optional comma-separated response fields. Overrides view."},
            "facets": {"type": "string", "description": "Optional WADL facets, e.g. pubyear;subjarea;openaccess."},
            "content": {"type": "string", "enum": ["core", "dummy", "all"], "description": "Scopus content category; default all."},
        },
        "required": ["query"],
    },
}

SCOPUS_ABSTRACT_SCHEMA = {
    "name": "scopus_abstract",
    "description": (
        "Retrieve one Scopus record and abstract by DOI, EID, Scopus ID, PII, PubMed ID, or PUI. "
        "Use this after scopus_search to obtain evidence for relevance screening. META_ABS is the "
        "recommended default; FULL may require institutional entitlement."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "identifier": {"type": "string", "description": "DOI/DOI URL, EID, Scopus ID, PII, PubMed ID, or PUI."},
            "identifier_type": {"type": "string", "enum": ["auto", "doi", "eid", "scopus_id", "pii", "pubmed_id", "pui"]},
            "view": {"type": "string", "enum": ["META", "META_ABS", "FULL", "REF", "ENTITLED"]},
        },
        "required": ["identifier"],
    },
}

SCOPUS_AUTHOR_SEARCH_SCHEMA = {
    "name": "scopus_author_search",
    "description": "Search official Scopus author profiles by name, ORCID-related query fields, affiliation, or author ID using Scopus Author Search syntax.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Author query, e.g. AUTHLASTNAME(Firdaus) AND AUTHFIRST(Rudi)."},
            "limit": {"type": "integer", "minimum": 1, "maximum": 25},
            "start": {"type": "integer", "minimum": 0, "maximum": 4999},
        },
        "required": ["query"],
    },
}

GOOGLE_SCHOLAR_SEARCH_SCHEMA = {
    "name": "google_scholar_search",
    "description": (
        "Search Google Scholar through SerpAPI, a third-party structured provider. Google does not "
        "offer an official public Scholar API. Use this to broaden discovery beyond Scopus and obtain "
        "Scholar citation counts, snippets, versions, related-article links, and available PDF links. "
        "Do not treat snippets as full abstracts; deduplicate against Scopus by DOI/title."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Natural Google Scholar query; quoting phrases and author: operators are supported by Scholar."},
            "limit": {"type": "integer", "minimum": 1, "maximum": 20},
            "start": {"type": "integer", "minimum": 0, "maximum": 990},
            "year_from": {"type": "integer", "minimum": 1000, "maximum": 3000},
            "year_to": {"type": "integer", "minimum": 1000, "maximum": 3000},
            "language": {"type": "string", "description": "Interface language code, e.g. en or id."},
            "sort_by_date": {"type": "boolean", "description": "True for newest-first; false for Scholar relevance order."},
        },
        "required": ["query"],
    },
}
