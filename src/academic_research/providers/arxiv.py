"""Dependency-free provider for the official arXiv Atom API."""

from __future__ import annotations

import re
import threading
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..models import Author, Paper, SearchResult

BASE_URL = "https://export.arxiv.org/api/query"
USER_AGENT = "academic-research-tools/0.1 (+https://github.com/OWNER/academic-research-tools)"
Transport = Callable[[str, dict[str, str], float], tuple[int, dict[str, str], bytes]]

_ATOM = "http://www.w3.org/2005/Atom"
_OPEN = "http://a9.com/-/spec/opensearch/1.1/"
_ARXIV = "http://arxiv.org/schemas/atom"
NS = {"atom": _ATOM, "open": _OPEN, "arxiv": _ARXIV}
_THROTTLE_LOCK = threading.Lock()
_LAST_REQUEST = 0.0


class ArxivAPIError(RuntimeError):
    """Raised when the arXiv API cannot satisfy a request."""

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _default_transport(
    url: str, headers: dict[str, str], timeout: float
) -> tuple[int, dict[str, str], bytes]:
    global _LAST_REQUEST
    # arXiv asks clients making repeated calls to wait at least three seconds.
    with _THROTTLE_LOCK:
        wait = 3.0 - (time.monotonic() - _LAST_REQUEST)
        if wait > 0:
            time.sleep(wait)
        request = Request(url, headers=headers, method="GET")
        try:
            with urlopen(request, timeout=timeout) as response:
                result = response.status, dict(response.headers.items()), response.read()
        except HTTPError as exc:
            result = exc.code, dict(exc.headers.items()) if exc.headers else {}, exc.read()
        except (URLError, TimeoutError) as exc:
            raise ArxivAPIError(f"Network error while calling arXiv API: {exc}") from exc
        finally:
            _LAST_REQUEST = time.monotonic()
        return result


def _text(node: ET.Element, path: str) -> str | None:
    found = node.find(path, NS)
    if found is None or found.text is None:
        return None
    value = re.sub(r"\s+", " ", found.text).strip()
    return value or None


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _year(value: str | None) -> int | None:
    if not value:
        return None
    match = re.match(r"^(\d{4})", value)
    return int(match.group(1)) if match else None


class ArxivProvider:
    """Search arXiv and normalize Atom entries into the shared paper contract."""

    source = "arxiv"

    def __init__(
        self,
        *,
        timeout: float = 30,
        transport: Transport | None = None,
        base_url: str = BASE_URL,
    ):
        self.timeout = max(1.0, min(float(timeout), 120.0))
        self.transport = transport or _default_transport
        self.base_url = base_url

    def search(
        self,
        query: str | None = None,
        *,
        ids: list[str] | str | None = None,
        limit: int = 10,
        start: int = 0,
        sort_by: str = "relevance",
        sort_order: str = "descending",
    ) -> SearchResult:
        query = str(query or "").strip() or None
        if isinstance(ids, str):
            ids = [item.strip() for item in ids.split(",") if item.strip()]
        normalized_ids = [str(item).strip() for item in (ids or []) if str(item).strip()]
        if not query and not normalized_ids:
            raise ValueError("query or ids is required")

        limit = max(1, min(_int(limit, 10), 100))
        start = max(0, min(_int(start, 0), 30000))
        sort_by = str(sort_by or "relevance")
        if sort_by not in {"relevance", "lastUpdatedDate", "submittedDate"}:
            raise ValueError("sort_by must be relevance, lastUpdatedDate, or submittedDate")
        sort_order = str(sort_order or "descending").lower()
        if sort_order not in {"ascending", "descending"}:
            raise ValueError("sort_order must be ascending or descending")

        params = {
            "search_query": query,
            "id_list": ",".join(normalized_ids) or None,
            "start": start,
            "max_results": limit,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }
        url = self.base_url + "?" + urlencode(
            {key: value for key, value in params.items() if value is not None}
        )
        status, _, body = self.transport(
            url,
            {"Accept": "application/atom+xml", "User-Agent": USER_AGENT},
            self.timeout,
        )
        if status >= 400:
            raise ArxivAPIError(f"arXiv API returned HTTP {status}", status_code=status)
        try:
            root = ET.fromstring(body)
        except ET.ParseError as exc:
            raise ArxivAPIError(
                "arXiv returned malformed Atom XML", status_code=status
            ) from exc

        papers: list[Paper] = []
        retrieved_at = datetime.now(timezone.utc).isoformat()
        for entry in root.findall("atom:entry", NS):
            entry_id = _text(entry, "atom:id")
            arxiv_id = re.sub(r"^https?://arxiv\.org/abs/", "", entry_id or "") or None
            if not arxiv_id:
                continue
            links: dict[tuple[str, str], str | None] = {}
            for link in entry.findall("atom:link", NS):
                rel = link.attrib.get("rel") or "alternate"
                links[(rel, link.attrib.get("type") or "")] = link.attrib.get("href")
            authors = [
                Author(
                    name=_text(author, "atom:name") or "Unknown",
                    affiliation=_text(author, "arxiv:affiliation"),
                )
                for author in entry.findall("atom:author", NS)
            ]
            categories = [
                item.attrib["term"]
                for item in entry.findall("atom:category", NS)
                if item.attrib.get("term")
            ]
            primary = entry.find("arxiv:primary_category", NS)
            published = _text(entry, "atom:published")
            primary_url = links.get(("alternate", "text/html")) or entry_id
            papers.append(
                Paper(
                    id=f"arxiv:{arxiv_id}",
                    title=_text(entry, "atom:title") or "Untitled",
                    source=self.source,
                    authors=authors,
                    abstract=_text(entry, "atom:summary"),
                    year=_year(published),
                    published=published,
                    updated=_text(entry, "atom:updated"),
                    doi=_text(entry, "arxiv:doi"),
                    primary_url=primary_url,
                    pdf_url=links.get(("related", "application/pdf")),
                    source_ids={"arxiv": arxiv_id},
                    categories=categories,
                    metadata={
                        "primary_category": (
                            primary.attrib.get("term") if primary is not None else None
                        ),
                        "journal_reference": _text(entry, "arxiv:journal_ref"),
                        "comment": _text(entry, "arxiv:comment"),
                    },
                    provenance={
                        "provider": "arXiv official API",
                        "retrieved_at": retrieved_at,
                        "query": query,
                    },
                )
            )

        total = _int(_text(root, "open:totalResults"))
        actual_start = _int(_text(root, "open:startIndex"), start)
        return SearchResult(
            source=self.source,
            query=query,
            total=total,
            offset=actual_start,
            limit=limit,
            next_offset=start + limit if start + limit < total else None,
            papers=papers,
            authenticated=False,
            attribution="Thank you to arXiv for use of its open access interoperability.",
            metadata={"ids": normalized_ids},
        )
