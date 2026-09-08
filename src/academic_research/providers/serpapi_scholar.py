"""Google Scholar discovery through optional third-party SerpAPI."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..models import Author, Paper, SearchResult, utc_now_iso

SERPAPI_URL = "https://serpapi.com/search.json"
Transport = Callable[[str, dict[str, str], float], tuple[int, dict[str, str], bytes]]


class SerpAPIError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _default_transport(
    url: str, headers: dict[str, str], timeout: float
) -> tuple[int, dict[str, str], bytes]:
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, dict(response.headers.items()), response.read()
    except HTTPError as exc:
        return exc.code, dict(exc.headers.items()) if exc.headers else {}, exc.read()
    except (URLError, TimeoutError) as exc:
        raise SerpAPIError(f"Network error while calling SerpAPI: {exc}") from exc


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class SerpAPIScholarProvider:
    """Optional Google Scholar discovery, explicitly not an official Google API."""

    name = "google_scholar"

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 30,
        transport: Transport | None = None,
        base_url: str = SERPAPI_URL,
    ):
        if not str(api_key or "").strip():
            raise ValueError("SERPAPI_API_KEY is required for Google Scholar search")
        self.api_key = api_key.strip()
        self.timeout = max(1.0, min(float(timeout), 120.0))
        self.transport = transport or _default_transport
        self.base_url = base_url

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        start: int = 0,
        year_from: int | None = None,
        year_to: int | None = None,
        language: str = "en",
        sort_by_date: bool = False,
    ) -> SearchResult:
        query = str(query or "").strip()
        if not query:
            raise ValueError("query is required")
        limit = max(1, min(_int(limit, 10), 20))
        start = max(0, min(_int(start, 0), 990))
        if year_from is not None:
            year_from = max(1000, min(_int(year_from), 3000))
        if year_to is not None:
            year_to = max(1000, min(_int(year_to), 3000))
        if year_from and year_to and year_from > year_to:
            raise ValueError("year_from cannot be greater than year_to")
        language = str(language or "en").strip().lower()[:5]
        params = {
            "engine": "google_scholar",
            "q": query,
            "api_key": self.api_key,
            "num": limit,
            "start": start,
            "hl": language,
            "as_ylo": year_from,
            "as_yhi": year_to,
            "scisbd": 1 if sort_by_date else None,
        }
        url = self.base_url + "?" + urlencode(
            {key: value for key, value in params.items() if value is not None}
        )
        status, _, body = self.transport(
            url,
            {
                "Accept": "application/json",
                "User-Agent": "Academic-Research-Tools/0.1",
            },
            self.timeout,
        )
        try:
            payload = json.loads(body.decode("utf-8", errors="replace")) if body else {}
        except json.JSONDecodeError as exc:
            raise SerpAPIError("SerpAPI returned a non-JSON response", status_code=status) from exc
        if status >= 400 or payload.get("error"):
            message = str(payload.get("error") or f"SerpAPI returned HTTP {status}")
            if status in {401, 403}:
                message += ". Check SERPAPI_API_KEY and account quota."
            elif status == 429:
                message += ". SerpAPI quota or rate limit reached."
            raise SerpAPIError(message, status_code=status)

        papers: list[Paper] = []
        retrieved_at = utc_now_iso()
        for item in payload.get("organic_results") or []:
            if not isinstance(item, dict):
                continue
            publication = item.get("publication_info") or {}
            inline = item.get("inline_links") or {}
            cited_by = inline.get("cited_by") or {}
            versions = inline.get("versions") or {}
            result_id = str(item.get("result_id") or "").strip() or None
            resources = item.get("resources") or []
            pdf_url = next(
                (
                    resource.get("link")
                    for resource in resources
                    if isinstance(resource, dict)
                    and (
                        str(resource.get("file_format") or "").upper() == "PDF"
                        or str(resource.get("title") or "").upper() == "PDF"
                    )
                ),
                None,
            )
            papers.append(
                Paper(
                    id=f"google_scholar:{result_id or item.get('position', 'unknown')}",
                    title=str(item.get("title") or "").strip(),
                    source=self.name,
                    abstract=None,
                    authors=[
                        Author(
                            name=str(author.get("name") or "").strip(),
                            author_id=str(author.get("author_id") or "").strip() or None,
                            profile_url=author.get("link"),
                        )
                        for author in publication.get("authors") or []
                        if isinstance(author, dict) and author.get("name")
                    ],
                    primary_url=item.get("link"),
                    pdf_url=pdf_url,
                    citation_count=_int(cited_by.get("total")),
                    source_ids={"google_scholar": result_id} if result_id else {},
                    metadata={
                        "position": item.get("position"),
                        "snippet": item.get("snippet"),
                        "publication_summary": publication.get("summary"),
                        "cited_by_url": cited_by.get("link"),
                        "versions_count": _int(versions.get("total")),
                        "versions_url": versions.get("link"),
                    },
                    provenance={
                        "provider": (
                            "Google Scholar via SerpAPI "
                            "(third-party; not an official Google API)"
                        ),
                        "retrieved_at": retrieved_at,
                        "abstract_kind": "unavailable",
                        "snippet_kind": "search_result_snippet",
                    },
                )
            )
        info = payload.get("search_information") or {}
        metadata = payload.get("search_metadata") or {}
        return SearchResult(
            provider=(
                "Google Scholar via SerpAPI "
                "(third-party; not an official Google API)"
            ),
            source=self.name,
            query=query,
            total=_int(info.get("total_results")),
            offset=start,
            limit=limit,
            next_offset=start + limit if papers else None,
            papers=papers,
            authenticated=True,
            metadata={"provider_status": metadata.get("status")},
        )
