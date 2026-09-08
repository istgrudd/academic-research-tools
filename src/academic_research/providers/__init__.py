"""Provider implementations for Academic Research Tools."""

from .arxiv import ArxivAPIError, ArxivProvider
from .scopus import ElsevierAPIError, ScopusProvider
from .semantic_scholar import SemanticScholarAPIError, SemanticScholarProvider
from .serpapi_scholar import SerpAPIError, SerpAPIScholarProvider

__all__ = [
    "ArxivAPIError",
    "ArxivProvider",
    "ElsevierAPIError",
    "ScopusProvider",
    "SemanticScholarAPIError",
    "SemanticScholarProvider",
    "SerpAPIError",
    "SerpAPIScholarProvider",
]
