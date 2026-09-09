"""Multi-provider academic search with deterministic deduplication."""

from __future__ import annotations

import copy
import re
import unicodedata
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .credentials import CredentialResolver
from .models import Author, Paper, SearchResult, UnifiedSearchResult
from .providers.arxiv import ArxivProvider
from .providers.scopus import ScopusProvider
from .providers.semantic_scholar import SemanticScholarProvider
from .providers.serpapi_scholar import SerpAPIScholarProvider


def _normalize_doi(value: str | None) -> str | None:
    text = str(value or "").strip().lower()
    text = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text)
    return text or None


def _normalize_title(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "").casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _dedupe_key(paper: Paper) -> tuple[str, str]:
    doi = _normalize_doi(paper.doi or paper.source_ids.get("doi"))
    if doi:
        return "doi", doi
    arxiv_id = paper.source_ids.get("arxiv")
    if arxiv_id:
        return "arxiv", re.sub(r"v\d+$", "", arxiv_id, flags=re.IGNORECASE)
    title = _normalize_title(paper.title)
    if title and paper.year:
        return "title_year", f"{title}|{paper.year}"
    return "source_id", f"{paper.source}|{paper.id}"


def _merge_authors(target: list[Author], incoming: list[Author]) -> list[Author]:
    seen = {_normalize_title(author.name) for author in target}
    for author in incoming:
        key = _normalize_title(author.name)
        if key and key not in seen:
            target.append(copy.deepcopy(author))
            seen.add(key)
    return target


def _merge_paper(target: Paper, incoming: Paper, key_kind: str) -> Paper:
    sources = target.provenance.setdefault("sources", [target.source])
    if incoming.source not in sources:
        sources.append(incoming.source)
    target.provenance["dedupe_key"] = key_kind
    records = target.provenance.setdefault(
        "records",
        [{"source": target.source, "id": target.id, **target.provenance}],
    )
    records.append({"source": incoming.source, "id": incoming.id, **incoming.provenance})

    target.source_ids.update(incoming.source_ids)
    if target.doi:
        target.doi = _normalize_doi(target.doi)
    elif incoming.doi:
        target.doi = _normalize_doi(incoming.doi)
        target.id = f"doi:{target.doi}"

    if incoming.abstract and (
        not target.abstract or len(incoming.abstract) > len(target.abstract)
    ):
        target.abstract = incoming.abstract
        target.provenance["abstract_source"] = incoming.source
    target.authors = _merge_authors(target.authors, incoming.authors)
    for attribute in ("published", "updated", "primary_url", "pdf_url", "venue"):
        if not getattr(target, attribute) and getattr(incoming, attribute):
            setattr(target, attribute, getattr(incoming, attribute))
    if target.year is None:
        target.year = incoming.year

    citation_counts = target.metadata.setdefault("citation_counts", {})
    if target.citation_count is not None:
        citation_counts.setdefault(target.source, target.citation_count)
    if incoming.citation_count is not None:
        citation_counts[incoming.source] = incoming.citation_count
        if target.citation_count is None:
            target.citation_count = incoming.citation_count
    return target


def deduplicate_papers(papers: list[Paper]) -> list[Paper]:
    """Deduplicate DOI-first, then arXiv ID, then normalized title and year."""
    merged: dict[tuple[str, str], Paper] = {}
    order: list[tuple[str, str]] = []
    for paper in papers:
        key = _dedupe_key(paper)
        if key not in merged:
            item = copy.deepcopy(paper)
            item.doi = _normalize_doi(item.doi)
            item.provenance.setdefault("sources", [item.source])
            item.provenance.setdefault("dedupe_key", key[0])
            if item.citation_count is not None:
                item.metadata.setdefault("citation_counts", {})[item.source] = (
                    item.citation_count
                )
            merged[key] = item
            order.append(key)
        else:
            _merge_paper(merged[key], paper, key[0])
    return [merged[key] for key in order]


class ResearchService:
    """Provider-neutral orchestration and partial-failure boundary."""

    def __init__(
        self,
        *,
        providers: dict[str, Any],
        redact: Callable[[str], str] | None = None,
    ):
        self.providers = dict(providers)
        self._redact = redact or (lambda text: text)

    @classmethod
    def from_environment(
        cls, *, resolver: CredentialResolver | None = None
    ) -> ResearchService:
        credentials = resolver or CredentialResolver()
        providers: dict[str, Any] = {
            "arxiv": ArxivProvider(),
            "semantic_scholar": SemanticScholarProvider(
                credentials.get("SEMANTIC_SCHOLAR_API_KEY")
            ),
        }
        elsevier_key = credentials.get("ELSEVIER_API_KEY")
        if elsevier_key:
            providers["scopus"] = ScopusProvider(
                elsevier_key,
                inst_token=credentials.get("ELSEVIER_INST_TOKEN"),
            )
        serpapi_key = credentials.get("SERPAPI_API_KEY")
        if serpapi_key:
            providers["google_scholar"] = SerpAPIScholarProvider(serpapi_key)
        return cls(providers=providers, redact=credentials.redact)

    def _search_one(
        self,
        source: str,
        query: str,
        limit: int,
        year: str | int | None,
    ) -> SearchResult:
        provider = self.providers[source]
        if source == "semantic_scholar":
            return provider.search(query, limit=limit, year=year)
        if source == "scopus":
            return provider.search(query, limit=limit, date=year)
        if source == "google_scholar" and year:
            text = str(year)
            if "-" in text:
                lower, upper = text.split("-", 1)
            else:
                lower = upper = text
            return provider.search(
                query,
                limit=limit,
                year_from=int(lower),
                year_to=int(upper),
            )
        return provider.search(query, limit=limit)

    def search(
        self,
        query: str,
        *,
        sources: list[str] | None = None,
        limit_per_source: int = 10,
        year: str | int | None = None,
    ) -> UnifiedSearchResult:
        query = str(query or "").strip()
        if not query:
            raise ValueError("query is required")
        requested = list(dict.fromkeys(sources or self.providers.keys()))
        if not requested:
            raise ValueError("at least one source is required")
        for source in requested:
            if source not in self.providers:
                raise ValueError(f"Unknown or unavailable source: {source}")
        limit = max(1, min(int(limit_per_source), 25))

        pages: dict[str, SearchResult] = {}
        errors: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=min(len(requested), 4)) as executor:
            future_sources = {
                executor.submit(self._search_one, source, query, limit, year): source
                for source in requested
            }
            for future in as_completed(future_sources):
                source = future_sources[future]
                try:
                    pages[source] = future.result()
                except Exception as exc:  # provider isolation boundary
                    errors[source] = self._redact(f"{type(exc).__name__}: {exc}")

        succeeded = [source for source in requested if source in pages]
        failed = [source for source in requested if source in errors]
        all_papers = [paper for source in succeeded for paper in pages[source].papers]
        deduplicated = deduplicate_papers(all_papers)
        warnings = [
            "Citation counts are provider-specific and must not be compared directly."
        ]
        if failed:
            warnings.append(
                "Some providers failed; results are partial: " + ", ".join(failed)
            )
        return UnifiedSearchResult(
            query=query,
            sources_requested=requested,
            sources_succeeded=succeeded,
            sources_failed=failed,
            retrieved_count=len(all_papers),
            deduplicated_count=len(deduplicated),
            papers=deduplicated,
            provider_totals={source: pages[source].total for source in succeeded},
            errors=errors,
            warnings=warnings,
        )