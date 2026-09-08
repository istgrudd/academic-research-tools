import json
from urllib.parse import parse_qs, urlparse

import pytest

from academic_research.providers.scopus import (
    ElsevierAPIError,
    ScopusProvider,
    detect_identifier_type,
)
from academic_research.providers.semantic_scholar import (
    SemanticScholarAPIError,
    SemanticScholarProvider,
)
from academic_research.providers.serpapi_scholar import SerpAPIScholarProvider


class FakeTransport:
    def __init__(self, payload, *, status=200, headers=None):
        self.payload = payload
        self.status = status
        self.headers = headers or {}
        self.calls = []

    def __call__(self, url, headers, timeout):
        self.calls.append({"url": url, "headers": headers, "timeout": timeout})
        body = (
            self.payload
            if isinstance(self.payload, bytes)
            else json.dumps(self.payload).encode()
        )
        return self.status, self.headers, body


S2_PAYLOAD = {
    "total": 7,
    "offset": 0,
    "next": 1,
    "data": [
        {
            "paperId": "paper-1",
            "corpusId": 123,
            "externalIds": {"DOI": "10.1000/Example", "ArXiv": "2501.12345"},
            "url": "https://www.semanticscholar.org/paper/paper-1",
            "title": "Vision Transformer for Recruitment",
            "abstract": "We study automated CV screening.",
            "venue": "ExampleConf",
            "year": 2025,
            "publicationDate": "2025-01-01",
            "authors": [{"authorId": "a1", "name": "Rudi Firdaus"}],
            "citationCount": 11,
            "influentialCitationCount": 2,
            "referenceCount": 30,
            "isOpenAccess": True,
            "openAccessPdf": {
                "url": "https://example.org/paper.pdf",
                "status": "GREEN",
                "license": "CCBY",
            },
            "fieldsOfStudy": ["Computer Science"],
            "s2FieldsOfStudy": [
                {"category": "Computer Science", "source": "s2-fos-model"}
            ],
            "publicationTypes": ["JournalArticle"],
            "publicationVenue": {
                "id": "v1",
                "name": "Example Conference",
                "type": "conference",
            },
            "journal": {"name": "Example Journal", "volume": "1", "pages": "1-10"},
        }
    ],
}


SCOPUS_SEARCH_PAYLOAD = {
    "search-results": {
        "opensearch:totalResults": "42",
        "opensearch:startIndex": "5",
        "opensearch:itemsPerPage": "1",
        "entry": [
            {
                "dc:identifier": "SCOPUS_ID:123",
                "eid": "2-s2.0-123",
                "dc:title": "Resume Ranking with BERT",
                "dc:creator": "Firdaus, R.",
                "prism:publicationName": "Example Journal",
                "prism:coverDate": "2025-02-01",
                "prism:doi": "10.1000/example",
                "citedby-count": "7",
                "subtypeDescription": "Article",
                "openaccess": "1",
                "authkeywords": "resume | recruitment | BERT",
                "link": [
                    {"@ref": "scopus", "@href": "https://scopus.example/123"}
                ],
            },
            {"error": "Result set was empty"},
        ],
    }
}


SCOPUS_ABSTRACT_PAYLOAD = {
    "abstracts-retrieval-response": {
        "coredata": {
            "dc:identifier": "SCOPUS_ID:123",
            "eid": "2-s2.0-123",
            "dc:title": "Resume Ranking with BERT",
            "dc:description": "We rank candidate resumes against job descriptions.",
            "prism:doi": "10.1000/example",
            "prism:publicationName": "Example Journal",
            "prism:coverDate": "2025-02-01",
            "citedby-count": "7",
        },
        "authors": {
            "author": [
                {
                    "@auid": "111",
                    "ce:indexed-name": "Firdaus R.",
                    "ce:given-name": "Rudi",
                    "ce:surname": "Firdaus",
                }
            ]
        },
        "subject-areas": {
            "subject-area": [
                {"$": "Computer Science", "@abbrev": "COMP", "@code": "1700"}
            ]
        },
    }
}


SCOPUS_AUTHOR_PAYLOAD = {
    "search-results": {
        "opensearch:totalResults": "1",
        "entry": [
            {
                "dc:identifier": "AUTHOR_ID:111",
                "eid": "9-s2.0-111",
                "preferred-name": {
                    "ce:indexed-name": "Firdaus R.",
                    "ce:given-name": "Rudi",
                    "ce:surname": "Firdaus",
                },
                "affiliation-current": {"affiliation-name": "Telkom University"},
                "document-count": "12",
                "citation-count": "34",
                "h-index": "4",
            }
        ],
    }
}


SERPAPI_PAYLOAD = {
    "search_metadata": {"status": "Success"},
    "search_information": {"total_results": 12345},
    "organic_results": [
        {
            "position": 1,
            "result_id": "abc123",
            "title": "AI Resume Screening with Transformers",
            "link": "https://example.org/paper",
            "snippet": "This is a search snippet, not a verified abstract.",
            "publication_info": {
                "summary": "R Firdaus, A Researcher - Example Journal, 2025",
                "authors": [
                    {
                        "name": "R Firdaus",
                        "author_id": "author1",
                        "link": "https://scholar.google.com/citations?user=author1",
                    }
                ],
            },
            "inline_links": {
                "cited_by": {"total": 17, "link": "https://example.org/cites"},
                "versions": {"total": 3, "link": "https://example.org/versions"},
            },
            "resources": [
                {
                    "title": "PDF",
                    "file_format": "PDF",
                    "link": "https://example.org/paper.pdf",
                }
            ],
        }
    ],
}


def test_semantic_scholar_normalizes_paper_and_authentication():
    transport = FakeTransport(S2_PAYLOAD)
    result = SemanticScholarProvider("s2-secret", transport=transport).search(
        "vision transformer", limit=1, year="2020-2026"
    )

    params = parse_qs(urlparse(transport.calls[0]["url"]).query)
    assert params["year"] == ["2020-2026"]
    assert transport.calls[0]["headers"]["x-api-key"] == "s2-secret"
    paper = result.papers[0]
    assert paper.id == "doi:10.1000/example"
    assert paper.source_ids["arxiv"] == "2501.12345"
    assert paper.citation_count == 11
    assert paper.pdf_url == "https://example.org/paper.pdf"
    assert result.authenticated is True
    assert result.next_offset == 1


def test_semantic_scholar_key_is_optional_and_rate_limit_is_actionable():
    transport = FakeTransport(S2_PAYLOAD)
    SemanticScholarProvider(transport=transport).search("test")
    assert "x-api-key" not in transport.calls[0]["headers"]

    limited = SemanticScholarProvider(
        transport=FakeTransport({"message": "Too Many Requests"}, status=429)
    )
    with pytest.raises(SemanticScholarAPIError, match="SEMANTIC_SCHOLAR_API_KEY"):
        limited.search("test")


def test_scopus_search_normalizes_and_preserves_quota():
    transport = FakeTransport(
        SCOPUS_SEARCH_PAYLOAD,
        headers={
            "X-RateLimit-Limit": "20000",
            "X-RateLimit-Remaining": "19999",
            "X-RateLimit-Reset": "1780000000",
        },
    )
    provider = ScopusProvider("elsevier-secret", inst_token="institution", transport=transport)
    result = provider.search(
        'TITLE-ABS-KEY("resume ranking")',
        limit=999,
        start=5,
        sort="relevance",
        date="2020-2026",
        subject_area="COMP",
    )

    call = transport.calls[0]
    params = parse_qs(urlparse(call["url"]).query)
    assert params["count"] == ["25"]
    assert params["sort"] == ["relevancy"]
    assert call["headers"]["X-ELS-APIKey"] == "elsevier-secret"
    assert call["headers"]["X-ELS-Insttoken"] == "institution"
    paper = result.papers[0]
    assert paper.id == "doi:10.1000/example"
    assert paper.source_ids["scopus"] == "123"
    assert paper.citation_count == 7
    assert paper.metadata["open_access"] is True
    assert result.quota["remaining"] == 19999


def test_scopus_abstract_author_search_and_identifier_detection():
    abstract_transport = FakeTransport(SCOPUS_ABSTRACT_PAYLOAD)
    detail = ScopusProvider("secret", transport=abstract_transport).get_abstract(
        "https://doi.org/10.1000/example", view="FULL"
    )
    assert detail["identifier_type"] == "doi"
    assert detail["paper"]["abstract"].startswith("We rank")
    assert detail["paper"]["authors"][0]["author_id"] == "111"
    assert detail["paper"]["categories"] == ["Computer Science"]

    author_transport = FakeTransport(SCOPUS_AUTHOR_PAYLOAD)
    authors = ScopusProvider("secret", transport=author_transport).search_authors(
        "AUTHLASTNAME(Firdaus)"
    )
    assert authors["results"][0]["name"] == "Firdaus R."
    assert authors["results"][0]["h_index"] == 4

    assert detect_identifier_type("10.1109/ACCESS.2025.123")[0] == "doi"
    assert detect_identifier_type("2-s2.0-85123456789")[0] == "eid"


def test_scopus_requires_own_key_and_reports_entitlement_errors():
    with pytest.raises(ValueError, match="ELSEVIER_API_KEY"):
        ScopusProvider("")

    payload = {
        "service-error": {
            "status": {
                "statusCode": "AUTHORIZATION_ERROR",
                "statusText": "Insufficient privileges",
            }
        }
    }
    provider = ScopusProvider("bad", transport=FakeTransport(payload, status=401))
    with pytest.raises(ElsevierAPIError, match="institutional"):
        provider.search("ALL(test)")


def test_serpapi_is_explicitly_third_party_and_snippet_is_not_abstract():
    transport = FakeTransport(SERPAPI_PAYLOAD)
    result = SerpAPIScholarProvider("serp-secret", transport=transport).search(
        "AI resume screening", year_from=2020, year_to=2026, language="id"
    )

    params = parse_qs(urlparse(transport.calls[0]["url"]).query)
    assert params["engine"] == ["google_scholar"]
    assert params["api_key"] == ["serp-secret"]
    paper = result.papers[0]
    assert paper.source == "google_scholar"
    assert paper.abstract is None
    assert paper.metadata["snippet"].startswith("This is a search snippet")
    assert paper.citation_count == 17
    assert "third-party" in result.provider.lower()

    with pytest.raises(ValueError, match="SERPAPI_API_KEY"):
        SerpAPIScholarProvider("")
