"""Hermes handlers for the Scopus research plugin."""

from __future__ import annotations

import json
import os
from typing import Any, Callable

from .arxiv_client import ArxivAPIError, ArxivClient
from .client import ElsevierAPIError, ElsevierClient
from .scholar_client import GoogleScholarClient
from .semantic_scholar_client import SemanticScholarAPIError, SemanticScholarClient


def _json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _client() -> ElsevierClient:
    return ElsevierClient(
        os.environ.get("ELSEVIER_API_KEY", ""),
        inst_token=os.environ.get("ELSEVIER_INST_TOKEN"),
    )


def _scholar_client() -> GoogleScholarClient:
    return GoogleScholarClient(os.environ.get("SERPAPI_API_KEY", ""))


def _semantic_scholar_client() -> SemanticScholarClient:
    return SemanticScholarClient(os.environ.get("SEMANTIC_SCHOLAR_API_KEY"))


def _limit(value: Any, default: int = 25) -> int:
    try:
        return max(1, min(int(value), 25))
    except (TypeError, ValueError):
        return default


def _start(value: Any) -> int:
    try:
        return max(0, min(int(value), 4999))
    except (TypeError, ValueError):
        return 0


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _run(operation: Callable[[], dict]) -> str:
    try:
        return _json({"success": True, **operation()})
    except (ElsevierAPIError, ArxivAPIError, SemanticScholarAPIError) as exc:
        return _json({
            "success": False,
            "error": str(exc),
            "status_code": getattr(exc, "status_code", None),
            "quota": getattr(exc, "quota", {}),
        })
    except (ValueError, TypeError) as exc:
        return _json({"success": False, "error": str(exc)})
    except Exception as exc:
        return _json({"success": False, "error": f"Research tool failed: {type(exc).__name__}: {exc}"})


def handle_arxiv_search(args: dict, **kwargs) -> str:
    del kwargs
    query = str(args.get("query") or "").strip() or None
    ids = args.get("ids")
    if not query and not ids:
        return _json({"success": False, "error": "query or ids is required"})
    return _run(lambda: ArxivClient().search(
        query,
        ids=ids,
        limit=max(1, min(int(args.get("limit") or 10), 100)),
        start=max(0, min(int(args.get("start") or 0), 30000)),
        sort_by=str(args.get("sort_by") or "relevance"),
        sort_order=str(args.get("sort_order") or "descending"),
    ))


def handle_semantic_scholar_search(args: dict, **kwargs) -> str:
    del kwargs
    query = str(args.get("query") or "").strip()
    if not query:
        return _json({"success": False, "error": "query is required"})
    return _run(lambda: _semantic_scholar_client().search(
        query,
        limit=max(1, min(int(args.get("limit") or 10), 100)),
        offset=max(0, min(int(args.get("offset") or 0), 9999)),
        year=args.get("year"),
    ))


def handle_scopus_search(args: dict, **kwargs) -> str:
    del kwargs
    query = str(args.get("query") or "").strip()
    if not query:
        return _json({"success": False, "error": "query is required"})
    return _run(lambda: _client().search(
        query,
        count=_limit(args.get("limit")),
        start=_start(args.get("start")),
        sort=args.get("sort"),
        view=str(args.get("view") or "STANDARD"),
        date=args.get("date"),
        subject_area=args.get("subject_area"),
        fields=args.get("fields"),
        facets=args.get("facets"),
        content=str(args.get("content") or "all"),
    ))


def handle_scopus_abstract(args: dict, **kwargs) -> str:
    del kwargs
    identifier = str(args.get("identifier") or "").strip()
    if not identifier:
        return _json({"success": False, "error": "identifier is required"})
    return _run(lambda: _client().get_abstract(
        identifier,
        identifier_type=str(args.get("identifier_type") or "auto"),
        view=str(args.get("view") or "META_ABS"),
    ))


def handle_scopus_author_search(args: dict, **kwargs) -> str:
    del kwargs
    query = str(args.get("query") or "").strip()
    if not query:
        return _json({"success": False, "error": "query is required"})
    return _run(lambda: _client().author_search(query, count=_limit(args.get("limit")), start=_start(args.get("start"))))


def handle_google_scholar_search(args: dict, **kwargs) -> str:
    del kwargs
    query = str(args.get("query") or "").strip()
    if not query:
        return _json({"success": False, "error": "query is required"})
    try:
        limit = max(1, min(int(args.get("limit") or 10), 20))
    except (TypeError, ValueError):
        limit = 10
    return _run(lambda: _scholar_client().search(
        query,
        limit=limit,
        start=_start(args.get("start")),
        year_from=args.get("year_from"),
        year_to=args.get("year_to"),
        language=str(args.get("language") or "en"),
        sort_by_date=_bool(args.get("sort_by_date")),
    ))
