"""Academic Research Tools public Python API."""

from .models import Author, Paper, SearchResult
from .providers.arxiv import ArxivAPIError, ArxivProvider
from .providers.scopus import ElsevierAPIError, ScopusProvider
from .providers.semantic_scholar import (
    SemanticScholarAPIError,
    SemanticScholarProvider,
)
from .providers.serpapi_scholar import SerpAPIError, SerpAPIScholarProvider

__all__ = [
    "ArxivAPIError",
    "ArxivProvider",
    "Author",
    "ElsevierAPIError",
    "Paper",
    "ScopusProvider",
    "SearchResult",
    "SemanticScholarAPIError",
    "SemanticScholarProvider",
    "SerpAPIError",
    "SerpAPIScholarProvider",
]
__version__ = "0.1.0"
