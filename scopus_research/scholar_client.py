"""Google Scholar search through SerpAPI.

Google does not provide an official public Scholar API. This adapter intentionally
uses a structured third-party provider instead of scraping scholar.google.com from
the user's VPS, which is brittle and commonly triggers CAPTCHA/IP blocks.
"""

from __future__ import annotations

import json
from typing import Any, Callable
from urllib.parse import urlencode

from .client import ElsevierAPIError, _default_transport, _int

Transport = Callable[[str, dict[str, str], float], tuple[int, dict[str, str], bytes]]
SERPAPI_URL = "https://serpapi.com/search.json"


class GoogleScholarClient:
    def __init__(self, api_key: str, *, timeout: float = 30, transport: Transport | None = None):
        if not str(api_key or "").strip():
            raise ValueError("SERPAPI_API_KEY is required for Google Scholar search")
        self.api_key = api_key.strip()
        self.timeout = max(1.0, min(float(timeout), 120.0))
        self.transport = transport or _default_transport

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
    ) -> dict[str, Any]:
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
        url = SERPAPI_URL + "?" + urlencode({k: v for k, v in params.items() if v is not None})
        status, response_headers, body = self.transport(
            url,
            {"Accept": "application/json", "User-Agent": "Hermes-Scopus-Research/1.1"},
            self.timeout,
        )
        try:
            payload = json.loads(body.decode("utf-8", errors="replace")) if body else {}
        except json.JSONDecodeError as exc:
            raise ElsevierAPIError("SerpAPI returned a non-JSON response", status_code=status) from exc
        if status >= 400 or payload.get("error"):
            message = str(payload.get("error") or f"Google Scholar provider returned HTTP {status}")
            if status in {401, 403}:
                message += ". Check SERPAPI_API_KEY and account quota."
            elif status == 429:
                message += ". SerpAPI quota or rate limit reached."
            raise ElsevierAPIError(message, status_code=status)

        papers = []
        for item in payload.get("organic_results") or []:
            if not isinstance(item, dict):
                continue
            pub = item.get("publication_info") or {}
            inline = item.get("inline_links") or {}
            cited_by = inline.get("cited_by") or {}
            versions = inline.get("versions") or {}
            resources = item.get("resources") or []
            pdf_url = next(
                (
                    resource.get("link")
                    for resource in resources
                    if isinstance(resource, dict)
                    and (str(resource.get("file_format") or "").upper() == "PDF" or str(resource.get("title") or "").upper() == "PDF")
                ),
                None,
            )
            authors = []
            for author in pub.get("authors") or []:
                if isinstance(author, dict):
                    authors.append({"name": author.get("name"), "author_id": author.get("author_id"), "profile_url": author.get("link")})
            papers.append(
                {
                    "position": item.get("position"),
                    "result_id": item.get("result_id"),
                    "title": item.get("title"),
                    "url": item.get("link"),
                    "snippet": item.get("snippet"),
                    "publication_summary": pub.get("summary"),
                    "authors": authors,
                    "cited_by_count": _int(cited_by.get("total")),
                    "cited_by_url": cited_by.get("link"),
                    "related_articles_url": inline.get("related_pages_link"),
                    "versions_count": _int(versions.get("total")),
                    "versions_url": versions.get("link"),
                    "pdf_url": pdf_url,
                }
            )
        info = payload.get("search_information") or {}
        metadata = payload.get("search_metadata") or {}
        return {
            "provider": "Google Scholar via SerpAPI (third-party; not an official Google API)",
            "query": query,
            "total_results": _int(info.get("total_results")),
            "start": start,
            "next_start": start + limit if papers else None,
            "results": papers,
            "provider_status": metadata.get("status"),
        }
