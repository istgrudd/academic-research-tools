"""Dependency-free client for the official arXiv Atom API."""
from __future__ import annotations

import re
import socket
import threading
import time
import xml.etree.ElementTree as ET
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://export.arxiv.org/api/query"
USER_AGENT = "Hermes-Agent-Research/1.0 (+https://github.com/NousResearch/hermes-agent)"
Transport = Callable[[str, dict[str, str], float], tuple[int, dict[str, str], bytes]]

_ATOM = "http://www.w3.org/2005/Atom"
_OPEN = "http://a9.com/-/spec/opensearch/1.1/"
_ARXIV = "http://arxiv.org/schemas/atom"
NS = {"atom": _ATOM, "open": _OPEN, "arxiv": _ARXIV}
_THROTTLE_LOCK = threading.Lock()
_LAST_REQUEST = 0.0


class ArxivAPIError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _default_transport(url: str, headers: dict[str, str], timeout: float) -> tuple[int, dict[str, str], bytes]:
    global _LAST_REQUEST
    # arXiv asks clients making repeated calls to wait three seconds.
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
        except (URLError, TimeoutError, socket.timeout) as exc:
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


class ArxivClient:
    def __init__(self, *, timeout: float = 30, transport: Transport | None = None, base_url: str = BASE_URL):
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
    ) -> dict[str, Any]:
        query = str(query or "").strip() or None
        if isinstance(ids, str):
            ids = [item.strip() for item in ids.split(",") if item.strip()]
        ids = [str(item).strip() for item in (ids or []) if str(item).strip()]
        if not query and not ids:
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
            "id_list": ",".join(ids) or None,
            "start": start,
            "max_results": limit,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }
        url = self.base_url + "?" + urlencode({k: v for k, v in params.items() if v is not None})
        status, _, body = self.transport(url, {"Accept": "application/atom+xml", "User-Agent": USER_AGENT}, self.timeout)
        if status >= 400:
            raise ArxivAPIError(f"arXiv API returned HTTP {status}", status_code=status)
        try:
            root = ET.fromstring(body)
        except ET.ParseError as exc:
            raise ArxivAPIError("arXiv returned malformed Atom XML", status_code=status) from exc

        papers = []
        for entry in root.findall("atom:entry", NS):
            entry_id = _text(entry, "atom:id")
            arxiv_id = re.sub(r"^https?://arxiv\.org/abs/", "", entry_id or "") or None
            links = {}
            for link in entry.findall("atom:link", NS):
                rel = link.attrib.get("rel") or "alternate"
                links[(rel, link.attrib.get("type") or "")] = link.attrib.get("href")
            authors = []
            for author in entry.findall("atom:author", NS):
                authors.append({
                    "name": _text(author, "atom:name"),
                    "affiliation": _text(author, "arxiv:affiliation"),
                })
            categories = [item.attrib.get("term") for item in entry.findall("atom:category", NS) if item.attrib.get("term")]
            primary = entry.find("arxiv:primary_category", NS)
            papers.append({
                "arxiv_id": arxiv_id,
                "title": _text(entry, "atom:title"),
                "abstract": _text(entry, "atom:summary"),
                "authors": authors,
                "published": _text(entry, "atom:published"),
                "updated": _text(entry, "atom:updated"),
                "categories": categories,
                "primary_category": primary.attrib.get("term") if primary is not None else None,
                "doi": _text(entry, "arxiv:doi"),
                "journal_reference": _text(entry, "arxiv:journal_ref"),
                "comment": _text(entry, "arxiv:comment"),
                "abstract_url": links.get(("alternate", "text/html")) or entry_id,
                "pdf_url": links.get(("related", "application/pdf")),
            })
        total = _int(_text(root, "open:totalResults"))
        actual_start = _int(_text(root, "open:startIndex"), start)
        items = _int(_text(root, "open:itemsPerPage"), len(papers))
        return {
            "provider": "arXiv official API",
            "query": query,
            "ids": ids,
            "total_results": total,
            "start": actual_start,
            "items_per_page": items,
            "next_start": start + limit if start + limit < total else None,
            "results": papers,
            "attribution": "Thank you to arXiv for use of its open access interoperability.",
        }
