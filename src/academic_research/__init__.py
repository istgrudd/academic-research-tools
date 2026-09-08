"""Academic Research Tools public Python API."""

from .models import Author, Paper, SearchResult
from .providers.arxiv import ArxivAPIError, ArxivProvider

__all__ = ["ArxivAPIError", "ArxivProvider", "Author", "Paper", "SearchResult"]
__version__ = "0.1.0"
