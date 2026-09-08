"""Official Semantic Scholar Academic Graph provider."""

from __future__ import annotations

import json
import re
import threading
import time
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..models import Author, Paper, SearchResult, utc_now_iso

BASE_URL = "https://api.semanticscholar.org/graph/v1"
FIELDS = ",".join(
    [
        "paperId",
        "corpusId",
        "externalIds",
        "url",
        "title",
        "abstract",
        "venue",
        "publicationVenue",
        "year",
        "publicationDate",
        "authors",
        "citationCount",
        "influentialCitationCount",
        "referenceCount",
        "isOpenAccess",
        "openAccessPdf",
        "fieldsOfStudy",
        "s2FieldsOfStudy",
        "publicationTypes",
        "journal",
    ]
)
Transport = Callable[[str, dict[str, str], float], tuple[int, dict[str, str], bytes]]
_THROTTLE_LOCK = threading.Lock()
_LAST_REQUEST = 0.0


class SemanticScholarAPIError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _default_transport(
    url: str, headers: dict[str, str], timeout: float
) -> tuple[int, dict[str, str], bytes]:
    global _LAST_REQUEST
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
        except (URLError, TimeoutError) as exc:
            raise SemanticScholarAPIError(
                f"Network error while calling Semantic Scholar API: {exc}"
            ) from exc
        finally:
            _LAST_REQUEST = time.monotonic()
        return result


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _stable_id(doi: str | None, paper_id: str | None) -> str:
    if doi:
        return f"doi:{doi.lower()}"
    return f"semantic_scholar:{paper_id or 'unknown'}"


class SemanticScholarProvider:
    """Search Semantic Scholar with an optional dedicated API key."""

    name = "semantic_scholar"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        timeout: float = 30,
        transport: Transport | None = None,
        base_url: str = BASE_URL,
    ):
        self.api_key = str(api_key or "").strip() or None
        self.timeout = max(1.0, min(float(timeout), 120.0))
        self.transport = transport or _default_transport
        self.base_url = base_url.rstrip("/")

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        offset: int = 0,
        year: str | int | None = None,
    ) -> SearchResult:
        query = str(query or "").strip()
        if not query:
            raise ValueError("query is required")
        limit = max(1, min(_int(limit, 10), 100))
        offset = max(0, min(_int(offset, 0), 9999))
        year_filter = str(year or "").strip() or None
        if year_filter and not re.fullmatch(r"\d{4}(?:-\d{4})?", year_filter):
            raise ValueError("year must be YYYY or YYYY-YYYY")

        params = {
            "query": query,
            "limit": limit,
            "offset": offset,
            "fields": FIELDS,
            "year": year_filter,
        }
        url = f"{self.base_url}/paper/search?" + urlencode(
            {key: value for key, value in params.items() if value is not None}
        )
        headers = {
            "Accept": "application/json",
            "User-Agent": "Academic-Research-Tools/0.1",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
        status, _, body = self.transport(url, headers, self.timeout)
        try:
            payload = json.loads(body.decode("utf-8", errors="replace")) if body else {}
        except json.JSONDecodeError as exc:
            raise SemanticScholarAPIError(
                "Semantic Scholar returned a non-JSON response", status_code=status
            ) from exc
        if status >= 400 or (isinstance(payload, dict) and payload.get("error")):
            detail = payload.get("message") or payload.get("error") or f"HTTP {status}"
            if status == 429:
                detail = (
                    f"{detail}. Rate limit reached; retry later or configure "
                    "SEMANTIC_SCHOLAR_API_KEY."
                )
            elif status in {401, 403}:
                detail = f"{detail}. Check SEMANTIC_SCHOLAR_API_KEY or call without a key."
            raise SemanticScholarAPIError(str(detail), status_code=status)

        papers: list[Paper] = []
        retrieved_at = utc_now_iso()
        for item in payload.get("data") or []:
            if not isinstance(item, dict):
                continue
            external = item.get("externalIds") or {}
            doi = str(external.get("DOI") or "").strip() or None
            paper_id = str(item.get("paperId") or "").strip() or None
            source_ids = {
                str(key).lower(): str(value)
                for key, value in external.items()
                if value is not None
            }
            if paper_id:
                source_ids["semantic_scholar"] = paper_id
            corpus_id = item.get("corpusId")
            if corpus_id is not None:
                source_ids["corpus"] = str(corpus_id)
            open_pdf = item.get("openAccessPdf") or {}
            publication_venue = item.get("publicationVenue") or {}
            journal = item.get("journal") or {}
            papers.append(
                Paper(
                    id=_stable_id(doi, paper_id),
                    title=str(item.get("title") or "").strip(),
                    source=self.name,
                    abstract=item.get("abstract"),
                    authors=[
                        Author(
                            name=str(author.get("name") or "").strip(),
                            author_id=str(author.get("authorId") or "").strip() or None,
                            profile_url=(
                                f"https://www.semanticscholar.org/author/"
                                f"{author.get('authorId')}"
                                if author.get("authorId")
                                else None
                            ),
                        )
                        for author in item.get("authors") or []
                        if isinstance(author, dict) and author.get("name")
                    ],
                    year=_int(item.get("year")) or None,
                    published=item.get("publicationDate"),
                    doi=doi.lower() if doi else None,
                    primary_url=item.get("url"),
                    pdf_url=open_pdf.get("url"),
                    venue=item.get("venue"),
                    citation_count=_int(item.get("citationCount")),
                    categories=item.get("fieldsOfStudy") or [],
                    source_ids=source_ids,
                    metadata={
                        "publication_venue": {
                            "id": publication_venue.get("id"),
                            "name": publication_venue.get("name"),
                            "type": publication_venue.get("type"),
                        },
                        "journal": {
                            "name": journal.get("name"),
                            "volume": journal.get("volume"),
                            "pages": journal.get("pages"),
                        },
                        "influential_citation_count": _int(
                            item.get("influentialCitationCount")
                        ),
                        "reference_count": _int(item.get("referenceCount")),
                        "is_open_access": bool(item.get("isOpenAccess")),
                        "open_access_pdf": open_pdf,
                        "s2_fields_of_study": item.get("s2FieldsOfStudy") or [],
                        "publication_types": item.get("publicationTypes") or [],
                    },
                    provenance={
                        "provider": "Semantic Scholar Academic Graph API",
                        "retrieved_at": retrieved_at,
                        "endpoint": "/paper/search",
                        "abstract_kind": "provider_abstract"
                        if item.get("abstract")
                        else "unavailable",
                    },
                )
            )

        next_value = payload.get("next")
        return SearchResult(
            provider="Semantic Scholar Academic Graph API",
            source=self.name,
            query=query,
            total=_int(payload.get("total")),
            offset=offset,
            limit=limit,
            next_offset=_int(next_value) if next_value is not None else None,
            papers=papers,
            authenticated=bool(self.api_key),
        )
