"""JSON schemas used by the native Hermes adapter."""

from __future__ import annotations

from typing import Any


def _schema(
    name: str,
    description: str,
    properties: dict[str, Any] | None = None,
    required: list[str] | None = None,
    *,
    any_of: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": properties or {},
    }
    if required:
        parameters["required"] = required
    if any_of:
        parameters["anyOf"] = any_of
    return {"name": name, "description": description, "parameters": parameters}


QUERY = {"type": "string", "description": "Academic literature search query."}
LIMIT_100 = {"type": "integer", "minimum": 1, "maximum": 100}
LIMIT_25 = {"type": "integer", "minimum": 1, "maximum": 25}
OFFSET = {"type": "integer", "minimum": 0}
YEAR = {"type": "string", "description": "YYYY or YYYY-YYYY."}

SCHEMAS = {
    "research_provider_status": _schema(
        "research_provider_status",
        "Report provider availability without exposing credential values.",
    ),
    "search_papers": _schema(
        "search_papers",
        "Search available scholarly sources and deduplicate with provenance.",
        {
            "query": QUERY,
            "sources": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "arxiv",
                        "semantic_scholar",
                        "scopus",
                        "google_scholar",
                    ],
                },
            },
            "limit_per_source": LIMIT_25,
            "year": YEAR,
        },
        ["query"],
    ),
    "search_arxiv": _schema(
        "search_arxiv",
        "Search or retrieve papers through the official public arXiv API.",
        {
            "query": QUERY,
            "ids": {"type": "array", "items": {"type": "string"}},
            "limit": LIMIT_100,
            "start": {"type": "integer", "minimum": 0, "maximum": 30000},
            "sort_by": {
                "type": "string",
                "enum": ["relevance", "lastUpdatedDate", "submittedDate"],
            },
            "sort_order": {
                "type": "string",
                "enum": ["ascending", "descending"],
            },
        },
        any_of=[{"required": ["query"]}, {"required": ["ids"]}],
    ),
    "search_semantic_scholar": _schema(
        "search_semantic_scholar",
        "Search the official Semantic Scholar Academic Graph API.",
        {
            "query": QUERY,
            "limit": LIMIT_100,
            "offset": {"type": "integer", "minimum": 0, "maximum": 9999},
            "year": YEAR,
        },
        ["query"],
    ),
    "search_scopus": _schema(
        "search_scopus",
        "Search the official Scopus index through the Elsevier API.",
        {
            "query": QUERY,
            "limit": LIMIT_25,
            "start": {"type": "integer", "minimum": 0, "maximum": 4999},
            "sort": {"type": "string"},
            "view": {"type": "string", "enum": ["STANDARD", "COMPLETE"]},
            "date": YEAR,
            "subject_area": {"type": "string"},
            "fields": {"type": "string"},
            "facets": {"type": "string"},
            "content": {"type": "string", "enum": ["core", "dummy", "all"]},
        },
        ["query"],
    ),
    "get_scopus_abstract": _schema(
        "get_scopus_abstract",
        "Retrieve normalized Scopus metadata and abstract by scholarly identifier.",
        {
            "identifier": {"type": "string"},
            "identifier_type": {
                "type": "string",
                "enum": [
                    "auto",
                    "doi",
                    "eid",
                    "scopus_id",
                    "pii",
                    "pubmed_id",
                    "pui",
                ],
            },
            "view": {
                "type": "string",
                "enum": ["META", "META_ABS", "FULL", "REF", "ENTITLED"],
            },
        },
        ["identifier"],
    ),
    "search_scopus_authors": _schema(
        "search_scopus_authors",
        "Search official Scopus author profiles.",
        {"query": QUERY, "limit": LIMIT_25, "start": OFFSET},
        ["query"],
    ),
    "search_google_scholar": _schema(
        "search_google_scholar",
        "Search Google Scholar through optional third-party SerpAPI.",
        {
            "query": QUERY,
            "limit": {"type": "integer", "minimum": 1, "maximum": 20},
            "start": {"type": "integer", "minimum": 0, "maximum": 990},
            "year_from": {"type": "integer", "minimum": 1000, "maximum": 3000},
            "year_to": {"type": "integer", "minimum": 1000, "maximum": 3000},
            "language": {"type": "string"},
            "sort_by_date": {"type": "boolean"},
        },
        ["query"],
    ),
}
