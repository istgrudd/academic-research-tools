"""Academic Research Tools public Python API."""

from .credentials import CredentialConfigError, CredentialResolver
from .models import Author, Paper, SearchResult, UnifiedSearchResult
from .providers.arxiv import ArxivAPIError, ArxivProvider
from .providers.scopus import ElsevierAPIError, ScopusProvider
from .providers.semantic_scholar import (
    SemanticScholarAPIError,
    SemanticScholarProvider,
)
from .providers.serpapi_scholar import SerpAPIError, SerpAPIScholarProvider
from .service import ResearchService, deduplicate_papers

__all__ = [
    "ArxivAPIError",
    "ArxivProvider",
    "Author",
    "CredentialConfigError",
    "CredentialResolver",
    "ElsevierAPIError",
    "Paper",
    "ResearchService",
    "ScopusProvider",
    "SearchResult",
    "SemanticScholarAPIError",
    "SemanticScholarProvider",
    "SerpAPIError",
    "SerpAPIScholarProvider",
    "UnifiedSearchResult",
    "deduplicate_papers",
]
__version__ = "0.2.0"
