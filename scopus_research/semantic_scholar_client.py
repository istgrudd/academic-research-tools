"""Dependency-free client for the official Semantic Scholar Academic Graph API."""
from __future__ import annotations

import json
import socket
import threading
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.semanticscholar.org/graph/v1"
FIELDS = ",".join([
    "paperId", "corpusId", "externalIds", "url", "title", "abstract", "venue",
    "publicationVenue", "year", "publicationDate", "authors", "citationCount",
    "influentialCitationCount", "referenceCount", "isOpenAccess", "openAccessPdf",
    "fieldsOfStudy", "s2FieldsOfStudy", "publicationTypes", "journal",
])
Transport = Callable[[str, dict[str, str], float], tuple[int, dict[str, str], bytes]]
_THROTTLE_LOCK = threading.Lock()
_LAST_REQUEST = 0.0


class SemanticScholarAPIError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _default_transport(url: str, headers: dict[str, str], timeout: float) -> tuple[int, dict[str, str], bytes]:
    global _LAST_REQUEST
    # Conservative 1 RPS guard; authenticated introductory limit is 1 RPS.
    with _THROTTLE_LOCK:
        wait = 1.0 - (time.monotonic() - _LAST_REQUEST)
        if wait > 0:
            time.sleep(wait)
        request = Request(url, headers=headers, method="GET")
        try:
            with urlopen(request, timeout=timeout) as response:
                result = response.status, dict(response.headers.items()), response.read()
        except HTTPError as exc:
            result = exc.code, dict(exc.headers.items()) if exc.headers else {}, exc.read()
        except (URLError, TimeoutError, socket.timeout) as exc:
            raise SemanticScholarAPIError(f"Network error while calling Semantic Scholar API: {exc}") from exc
        finally:
            _LAST_REQUEST = time.monotonic()
        return result


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class SemanticScholarClient:
    def __init__(self, api_key: str | None = None, *, timeout: float = 30, transport: Transport | None = None, base_url: str = BASE_URL):
        self.api_key = str(api_key or "").strip() or None
        self.timeout = max(1.0, min(float(timeout), 120.0))
        self.transport = transport or _default_transport
        self.base_url = base_url.rstrip("/")

    def search(self, query: str, *, limit: int = 10, offset: int = 0, year: str | int | None = None) -> dict[str, Any]:
        query = str(query or "").strip()
        if not query:
            raise ValueError("query is required")
        limit = max(1, min(_int(limit, 10), 100))
        offset = max(0, min(_int(offset, 0), 9999))
        year = str(year or "").strip() or None
        if year:
            import re
            if not re.fullmatch(r"\d{4}(?:-\d{4})?", year):
                raise ValueError("year must be YYYY or YYYY-YYYY")
        params = {"query": query, "limit": limit, "offset": offset, "fields": FIELDS, "year": year}
        url = f"{self.base_url}/paper/search?" + urlencode({k: v for k, v in params.items() if v is not None})
        headers = {"Accept": "application/json", "User-Agent": "Hermes-Agent-Research/1.0"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        status, _, body = self.transport(url, headers, self.timeout)
        try:
            payload = json.loads(body.decode("utf-8", errors="replace")) if body else {}
        except json.JSONDecodeError as exc:
            raise SemanticScholarAPIError("Semantic Scholar returned a non-JSON response", status_code=status) from exc
        if status >= 400 or (isinstance(payload, dict) and payload.get("error")):
            detail = payload.get("message") or payload.get("error") or f"HTTP {status}"
            if status == 429:
                detail = f"{detail}. Rate limit reached; retry later or configure SEMANTIC_SCHOLAR_API_KEY."
            elif status in {401, 403}:
                detail = f"{detail}. Check SEMANTIC_SCHOLAR_API_KEY or call without a key."
            raise SemanticScholarAPIError(str(detail), status_code=status)

        papers = []
        for item in payload.get("data") or []:
            if not isinstance(item, dict):
                continue
            oa = item.get("openAccessPdf") or {}
            venue = item.get("publicationVenue") or {}
            journal = item.get("journal") or {}
            authors = [
                {"author_id": a.get("authorId"), "name": a.get("name")}
                for a in (item.get("authors") or []) if isinstance(a, dict)
            ]
            papers.append({
                "paper_id": item.get("paperId"),
                "corpus_id": item.get("corpusId"),
                "external_ids": item.get("externalIds") or {},
                "title": item.get("title"),
                "abstract": item.get("abstract"),
                "authors": authors,
                "year": item.get("year"),
                "publication_date": item.get("publicationDate"),
                "venue": item.get("venue"),
                "publication_venue": {"id": venue.get("id"), "name": venue.get("name"), "type": venue.get("type")},
                "journal": {"name": journal.get("name"), "volume": journal.get("volume"), "pages": journal.get("pages")},
                "citation_count": _int(item.get("citationCount")),
                "influential_citation_count": _int(item.get("influentialCitationCount")),
                "reference_count": _int(item.get("referenceCount")),
                "is_open_access": bool(item.get("isOpenAccess")),
                "open_access_pdf": {"url": oa.get("url"), "status": oa.get("status"), "license": oa.get("license")},
                "fields_of_study": item.get("fieldsOfStudy") or [],
                "s2_fields_of_study": item.get("s2FieldsOfStudy") or [],
                "publication_types": item.get("publicationTypes") or [],
                "url": item.get("url"),
            })
        total = _int(payload.get("total"))
        next_offset = payload.get("next")
        return {
            "provider": "Semantic Scholar Academic Graph API",
            "query": query,
            "year": year,
            "total_results": total,
            "offset": offset,
            "next_offset": _int(next_offset) if next_offset is not None else None,
            "results": papers,
            "authenticated": bool(self.api_key),
        }
