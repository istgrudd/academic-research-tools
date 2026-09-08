"""Official Elsevier Scopus Search, Abstract, and Author providers."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from ..models import Author, Paper, SearchResult, utc_now_iso

BASE_URL = "https://api.elsevier.com"
Transport = Callable[[str, dict[str, str], float], tuple[int, dict[str, str], bytes]]


class ElsevierAPIError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        quota: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.quota = quota or {}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "open"}


def _strip_scopus_id(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return re.sub(r"^SCOPUS_ID:", "", text, flags=re.IGNORECASE)


def _year(value: Any) -> int | None:
    match = re.match(r"^(\d{4})", str(value or ""))
    return int(match.group(1)) if match else None


def detect_identifier_type(identifier: str) -> tuple[str, str]:
    """Return an Abstract Retrieval API identifier type and normalized value."""
    value = str(identifier or "").strip()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
    if not value:
        raise ValueError("identifier is required")
    if re.match(r"^10\.\d{4,9}/\S+$", value, flags=re.IGNORECASE):
        return "doi", value
    if value.lower().startswith("2-s2.0-"):
        return "eid", value
    if value.upper().startswith("SCOPUS_ID:"):
        return "scopus_id", value.split(":", 1)[1]
    if value.isdigit():
        return "scopus_id", value
    raise ValueError("Could not detect identifier type; provide identifier_type explicitly")


def _quota(headers: dict[str, str]) -> dict[str, Any]:
    lowered = {str(key).lower(): value for key, value in headers.items()}
    result: dict[str, Any] = {}
    mapping = {
        "limit": "x-ratelimit-limit",
        "remaining": "x-ratelimit-remaining",
        "reset": "x-ratelimit-reset",
    }
    for output_key, header_key in mapping.items():
        raw = lowered.get(header_key)
        if raw is not None:
            result[output_key] = _int(raw) if output_key != "reset" else raw
    return result


def _error_text(payload: Any) -> str:
    if isinstance(payload, dict):
        status = payload.get("service-error", {}).get("status", {})
        if isinstance(status, dict):
            text = status.get("statusText") or status.get("statusCode")
            if text:
                return str(text)
        for key in ("error-response", "error", "message"):
            value = payload.get(key)
            if isinstance(value, dict):
                value = value.get("error-message") or value.get("message")
            if value:
                return str(value)
    return "Unknown Elsevier API error"


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
        raise ElsevierAPIError(f"Network error while calling Elsevier API: {exc}") from exc


def _paper_id(doi: str | None, scopus_id: str | None, eid: str | None) -> str:
    if doi:
        return f"doi:{doi.lower()}"
    if scopus_id:
        return f"scopus:{scopus_id}"
    return f"scopus:{eid or 'unknown'}"


class ScopusProvider:
    """Scopus API provider requiring a user-supplied Elsevier API key."""

    name = "scopus"

    def __init__(
        self,
        api_key: str,
        *,
        inst_token: str | None = None,
        timeout: float = 30,
        transport: Transport | None = None,
        base_url: str = BASE_URL,
    ):
        if not str(api_key or "").strip():
            raise ValueError("ELSEVIER_API_KEY is required")
        self.api_key = api_key.strip()
        self.inst_token = str(inst_token or "").strip() or None
        self.timeout = max(1.0, min(float(timeout), 120.0))
        self.transport = transport or _default_transport
        self.base_url = base_url.rstrip("/")

    def _request(
        self, path: str, params: dict[str, Any] | None = None
    ) -> tuple[Any, dict[str, Any]]:
        clean_params = {
            key: value
            for key, value in (params or {}).items()
            if value is not None and value != ""
        }
        url = f"{self.base_url}{path}"
        if clean_params:
            url += "?" + urlencode(clean_params)
        headers = {
            "Accept": "application/json",
            "X-ELS-APIKey": self.api_key,
            "User-Agent": "Academic-Research-Tools/0.1",
        }
        if self.inst_token:
            headers["X-ELS-Insttoken"] = self.inst_token
        status, response_headers, body = self.transport(url, headers, self.timeout)
        quota = _quota(response_headers)
        try:
            payload = json.loads(body.decode("utf-8", errors="replace")) if body else {}
        except json.JSONDecodeError as exc:
            raise ElsevierAPIError(
                "Elsevier returned a non-JSON response; check API entitlement "
                "or service availability",
                status_code=status,
                quota=quota,
            ) from exc
        if status >= 400:
            detail = _error_text(payload)
            if status in {401, 403}:
                detail += (
                    ". Check the API key and institutional Scopus entitlement, "
                    "campus/VPN IP, or ELSEVIER_INST_TOKEN."
                )
            elif status == 429:
                detail += (
                    ". Scopus quota or throttle reached; retry after the reported reset time."
                )
            raise ElsevierAPIError(detail, status_code=status, quota=quota)
        return payload, quota

    def search(
        self,
        query: str,
        *,
        limit: int = 25,
        start: int = 0,
        sort: str | None = None,
        view: str = "STANDARD",
        date: str | None = None,
        subject_area: str | None = None,
        fields: str | None = None,
        facets: str | None = None,
        content: str = "all",
    ) -> SearchResult:
        query = str(query or "").strip()
        if not query:
            raise ValueError("query is required")
        limit = max(1, min(_int(limit, 25), 25))
        start = max(0, min(_int(start, 0), 4999))
        view = str(view or "STANDARD").upper()
        if view not in {"STANDARD", "COMPLETE"}:
            raise ValueError("view must be STANDARD or COMPLETE")

        sort = str(sort or "").strip() or None
        if sort:
            sort_parts: list[str] = []
            valid_sort_fields = {
                "artnum",
                "citedby-count",
                "coverDate",
                "creator",
                "orig-load-date",
                "pagecount",
                "pagefirst",
                "pageRange",
                "publicationName",
                "pubyear",
                "relevancy",
                "volume",
            }
            for part in sort.split(",")[:3]:
                part = part.strip()
                sign = part[0] if part[:1] in {"+", "-"} else ""
                field_name = part[1:] if sign else part
                if field_name.lower() in {"relevance", "relevancy"}:
                    field_name = "relevancy"
                if field_name not in valid_sort_fields:
                    raise ValueError(f"Unsupported Scopus sort field: {field_name}")
                sort_parts.append(sign + field_name)
            sort = ",".join(sort_parts)

        date = str(date or "").strip() or None
        if date and not re.fullmatch(r"\d{4}(?:-\d{4})?", date):
            raise ValueError("date must be YYYY or YYYY-YYYY")
        subject_area = str(subject_area or "").strip().upper() or None
        valid_subjects = {
            "AGRI",
            "ARTS",
            "BIOC",
            "BUSI",
            "CENG",
            "CHEM",
            "COMP",
            "DECI",
            "DENT",
            "EART",
            "ECON",
            "ENER",
            "ENGI",
            "ENVI",
            "HEAL",
            "IMMU",
            "MATE",
            "MATH",
            "MEDI",
            "NEUR",
            "NURS",
            "PHAR",
            "PHYS",
            "PSYC",
            "SOCI",
            "VETE",
            "MULT",
        }
        if subject_area and subject_area not in valid_subjects:
            raise ValueError(f"Unknown Scopus subject-area code: {subject_area}")
        fields = str(fields or "").strip() or None
        facets = str(facets or "").strip() or None
        content = str(content or "all").lower()
        if content not in {"core", "dummy", "all"}:
            raise ValueError("content must be core, dummy, or all")

        payload, quota = self._request(
            "/content/search/scopus",
            {
                "query": query,
                "count": limit,
                "start": start,
                "sort": sort,
                "view": view,
                "date": date,
                "subj": subject_area,
                "field": fields,
                "facets": facets,
                "content": content,
            },
        )
        root = payload.get("search-results", {}) if isinstance(payload, dict) else {}
        retrieved_at = utc_now_iso()
        papers: list[Paper] = []
        for entry in _as_list(root.get("entry")):
            if not isinstance(entry, dict) or entry.get("error"):
                continue
            links = {
                item.get("@ref"): item.get("@href")
                for item in _as_list(entry.get("link"))
                if isinstance(item, dict)
            }
            doi = str(entry.get("prism:doi") or "").strip() or None
            scopus_id = _strip_scopus_id(entry.get("dc:identifier"))
            eid = str(entry.get("eid") or "").strip() or None
            source_ids: dict[str, str] = {}
            if doi:
                source_ids["doi"] = doi.lower()
            if scopus_id:
                source_ids["scopus"] = scopus_id
            if eid:
                source_ids["eid"] = eid
            first_author = str(entry.get("dc:creator") or "").strip() or None
            cover_date = entry.get("prism:coverDate")
            papers.append(
                Paper(
                    id=_paper_id(doi, scopus_id, eid),
                    title=str(entry.get("dc:title") or "").strip(),
                    source=self.name,
                    abstract=entry.get("dc:description"),
                    authors=[Author(name=first_author)] if first_author else [],
                    year=_year(cover_date),
                    published=cover_date,
                    doi=doi.lower() if doi else None,
                    primary_url=links.get("scopus"),
                    venue=entry.get("prism:publicationName"),
                    citation_count=_int(entry.get("citedby-count")),
                    source_ids=source_ids,
                    metadata={
                        "document_type": entry.get("subtypeDescription")
                        or entry.get("subtype"),
                        "open_access": _bool(entry.get("openaccess")),
                        "author_keywords": entry.get("authkeywords"),
                    },
                    provenance={
                        "provider": "Elsevier Scopus APIs",
                        "retrieved_at": retrieved_at,
                        "endpoint": "/content/search/scopus",
                        "abstract_kind": "provider_abstract"
                        if entry.get("dc:description")
                        else "unavailable",
                    },
                )
            )
        total = _int(root.get("opensearch:totalResults"))
        actual_start = _int(root.get("opensearch:startIndex"), start)
        return SearchResult(
            provider="Elsevier Scopus Search API",
            source=self.name,
            query=query,
            total=total,
            offset=actual_start,
            limit=limit,
            next_offset=start + limit if start + limit < total else None,
            papers=papers,
            authenticated=True,
            quota=quota,
        )

    def get_abstract(
        self,
        identifier: str,
        *,
        identifier_type: str = "auto",
        view: str = "META_ABS",
    ) -> dict[str, Any]:
        if identifier_type == "auto":
            identifier_type, identifier = detect_identifier_type(identifier)
        else:
            identifier_type = str(identifier_type or "").strip().lower()
            identifier = str(identifier or "").strip()
        allowed_types = {"doi", "eid", "scopus_id", "pii", "pubmed_id", "pui"}
        if identifier_type not in allowed_types:
            allowed = ", ".join(sorted(allowed_types))
            raise ValueError(f"identifier_type must be one of: auto, {allowed}")
        if not identifier:
            raise ValueError("identifier is required")
        view = str(view or "META_ABS").upper()
        if view not in {"META", "META_ABS", "FULL", "REF", "ENTITLED"}:
            raise ValueError("view must be META, META_ABS, FULL, REF, or ENTITLED")
        safe_identifier = quote(identifier, safe="/")
        payload, quota = self._request(
            f"/content/abstract/{identifier_type}/{safe_identifier}", {"view": view}
        )
        root = payload.get("abstracts-retrieval-response", {}) if isinstance(payload, dict) else {}
        core = root.get("coredata", {}) if isinstance(root, dict) else {}
        authors: list[Author] = []
        for author in _as_list(
            (root.get("authors") or {}).get("author") if isinstance(root, dict) else None
        ):
            if not isinstance(author, dict):
                continue
            name = author.get("ce:indexed-name") or " ".join(
                filter(None, [author.get("ce:given-name"), author.get("ce:surname")])
            )
            if name:
                authors.append(
                    Author(
                        name=str(name),
                        author_id=str(author.get("@auid") or "").strip() or None,
                    )
                )
        categories: list[str] = []
        subject_metadata: list[dict[str, Any]] = []
        raw_subjects = (
            (root.get("subject-areas") or {}).get("subject-area")
            if isinstance(root, dict)
            else None
        )
        for subject in _as_list(raw_subjects):
            if not isinstance(subject, dict):
                continue
            if subject.get("$"):
                categories.append(str(subject["$"]))
            subject_metadata.append(
                {
                    "name": subject.get("$"),
                    "abbreviation": subject.get("@abbrev"),
                    "code": subject.get("@code"),
                }
            )
        abstract = core.get("dc:description")
        if not abstract:
            head = (
                (((root.get("item") or {}).get("bibrecord") or {}).get("head") or {})
                if isinstance(root, dict)
                else {}
            )
            abstract = head.get("abstracts")
        doi = str(core.get("prism:doi") or "").strip() or None
        scopus_id = _strip_scopus_id(core.get("dc:identifier"))
        eid = str(core.get("eid") or "").strip() or None
        source_ids: dict[str, str] = {}
        if doi:
            source_ids["doi"] = doi.lower()
        if scopus_id:
            source_ids["scopus"] = scopus_id
        if eid:
            source_ids["eid"] = eid
        cover_date = core.get("prism:coverDate")
        paper = Paper(
            id=_paper_id(doi, scopus_id, eid),
            title=str(core.get("dc:title") or "").strip(),
            source=self.name,
            abstract=abstract,
            authors=authors,
            year=_year(cover_date),
            published=cover_date,
            doi=doi.lower() if doi else None,
            venue=core.get("prism:publicationName"),
            citation_count=_int(core.get("citedby-count")),
            source_ids=source_ids,
            categories=categories,
            metadata={"subject_areas": subject_metadata, "view": view},
            provenance={
                "provider": "Elsevier Scopus Abstract Retrieval API",
                "retrieved_at": utc_now_iso(),
                "endpoint": f"/content/abstract/{identifier_type}/...",
                "abstract_kind": "provider_abstract" if abstract else "unavailable",
            },
        )
        return {
            "identifier_type": identifier_type,
            "identifier": identifier,
            "view": view,
            "paper": paper.to_dict(),
            "quota": quota,
        }

    def search_authors(
        self, query: str, *, limit: int = 25, start: int = 0
    ) -> dict[str, Any]:
        query = str(query or "").strip()
        if not query:
            raise ValueError("query is required")
        limit = max(1, min(_int(limit, 25), 25))
        start = max(0, min(_int(start, 0), 4999))
        payload, quota = self._request(
            "/content/search/author",
            {"query": query, "count": limit, "start": start, "view": "STANDARD"},
        )
        root = payload.get("search-results", {}) if isinstance(payload, dict) else {}
        authors: list[dict[str, Any]] = []
        for entry in _as_list(root.get("entry")):
            if not isinstance(entry, dict) or entry.get("error"):
                continue
            preferred = entry.get("preferred-name") or {}
            affiliation = entry.get("affiliation-current") or {}
            authors.append(
                {
                    "author_id": str(entry.get("dc:identifier") or "").replace(
                        "AUTHOR_ID:", ""
                    )
                    or None,
                    "eid": entry.get("eid"),
                    "name": preferred.get("ce:indexed-name")
                    or entry.get("ce:indexed-name"),
                    "given_name": preferred.get("ce:given-name"),
                    "surname": preferred.get("ce:surname"),
                    "affiliation": affiliation.get("affiliation-name")
                    if isinstance(affiliation, dict)
                    else None,
                    "document_count": _int(entry.get("document-count")),
                    "citation_count": _int(entry.get("citation-count")),
                    "h_index": _int(entry.get("h-index")),
                }
            )
        return {
            "provider": "Elsevier Scopus Author Search API",
            "source": self.name,
            "query": query,
            "total_results": _int(root.get("opensearch:totalResults")),
            "offset": start,
            "limit": limit,
            "results": authors,
            "quota": quota,
        }
