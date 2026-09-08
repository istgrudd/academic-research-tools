"""Harness-neutral data contracts for academic literature providers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    """Return an RFC 3339 UTC timestamp for retrieval provenance."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(slots=True)
class Author:
    """A normalized scholarly author."""

    name: str
    author_id: str | None = None
    affiliation: str | None = None
    profile_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Paper:
    """Provider-neutral paper metadata with explicit source provenance."""

    id: str
    title: str
    source: str
    authors: list[Author] = field(default_factory=list)
    abstract: str | None = None
    year: int | None = None
    published: str | None = None
    updated: str | None = None
    doi: str | None = None
    primary_url: str | None = None
    pdf_url: str | None = None
    venue: str | None = None
    citation_count: int | None = None
    source_ids: dict[str, str] = field(default_factory=dict)
    categories: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SearchResult:
    """A normalized page of search results from one or more providers."""

    source: str
    query: str | None
    papers: list[Paper]
    provider: str | None = None
    total: int = 0
    offset: int = 0
    limit: int = 0
    next_offset: int | None = None
    authenticated: bool | None = None
    attribution: str | None = None
    warnings: list[str] = field(default_factory=list)
    quota: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "provider": self.provider,
            "query": self.query,
            "total_results": self.total,
            "offset": self.offset,
            "limit": self.limit,
            "next_offset": self.next_offset,
            "authenticated": self.authenticated,
            "attribution": self.attribution,
            "warnings": list(self.warnings),
            "quota": dict(self.quota),
            "metadata": dict(self.metadata),
            "results": [paper.to_dict() for paper in self.papers],
        }


@dataclass(slots=True)
class UnifiedSearchResult:
    """Auditable result of a best-effort search across multiple providers."""

    query: str
    sources_requested: list[str]
    sources_succeeded: list[str]
    sources_failed: list[str]
    retrieved_count: int
    deduplicated_count: int
    papers: list[Paper]
    provider_totals: dict[str, int] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "sources_requested": list(self.sources_requested),
            "sources_succeeded": list(self.sources_succeeded),
            "sources_failed": list(self.sources_failed),
            "retrieved_count": self.retrieved_count,
            "deduplicated_count": self.deduplicated_count,
            "provider_totals": dict(self.provider_totals),
            "errors": dict(self.errors),
            "warnings": list(self.warnings),
            "results": [paper.to_dict() for paper in self.papers],
        }
