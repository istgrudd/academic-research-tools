import json
import os
import sys
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PLUGIN_PARENT = Path(__file__).resolve().parents[2]
if str(PLUGIN_PARENT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_PARENT))

from scopus_research.client import ElsevierAPIError, ElsevierClient, detect_identifier_type
from scopus_research.scholar_client import GoogleScholarClient
from scopus_research.tools import (
    handle_google_scholar_search,
    handle_scopus_abstract,
    handle_scopus_search,
)


SEARCH_PAYLOAD = {
    "search-results": {
        "opensearch:totalResults": "42",
        "opensearch:startIndex": "0",
        "opensearch:itemsPerPage": "2",
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
                "link": [{"@ref": "scopus", "@href": "https://scopus.example/123"}],
            },
            {"error": "Result set was empty"},
        ],
    }
}

ABSTRACT_PAYLOAD = {
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
                {"@auid": "111", "ce:indexed-name": "Firdaus R.", "ce:given-name": "Rudi", "ce:surname": "Firdaus"}
            ]
        },
        "subject-areas": {"subject-area": [{"$": "Computer Science", "@abbrev": "COMP"}]},
    }
}


class FakeTransport:
    def __init__(self, payload, status=200, response_headers=None):
        self.payload = payload
        self.status = status
        self.response_headers = response_headers or {
            "X-RateLimit-Limit": "20000",
            "X-RateLimit-Remaining": "19999",
            "X-RateLimit-Reset": "1780000000",
        }
        self.calls = []

    def __call__(self, url, headers, timeout):
        self.calls.append({"url": url, "headers": headers, "timeout": timeout})
        body = self.payload if isinstance(self.payload, bytes) else json.dumps(self.payload).encode()
        return self.status, self.response_headers, body


class ClientTests(unittest.TestCase):
    def test_search_encodes_query_caps_count_and_normalizes_records(self):
        transport = FakeTransport(SEARCH_PAYLOAD)
        client = ElsevierClient("secret", inst_token="institution", transport=transport)
        result = client.search(
            'TITLE-ABS-KEY("resume ranking")',
            count=999,
            start=5,
            sort="relevance",
            date="2020-2026",
            subject_area="COMP",
            fields="dc:title,prism:doi",
            facets="pubyear;subjarea",
        )

        call = transport.calls[0]
        parsed = urlparse(call["url"])
        params = parse_qs(parsed.query)
        self.assertEqual(parsed.path, "/content/search/scopus")
        self.assertEqual(params["query"], ['TITLE-ABS-KEY("resume ranking")'])
        self.assertEqual(params["count"], ["25"])
        self.assertEqual(params["start"], ["5"])
        self.assertEqual(params["sort"], ["relevancy"])
        self.assertEqual(params["date"], ["2020-2026"])
        self.assertEqual(params["subj"], ["COMP"])
        self.assertEqual(params["field"], ["dc:title,prism:doi"])
        self.assertEqual(params["facets"], ["pubyear;subjarea"])
        self.assertEqual(call["headers"]["X-ELS-APIKey"], "secret")
        self.assertEqual(call["headers"]["X-ELS-Insttoken"], "institution")
        self.assertEqual(result["total_results"], 42)
        self.assertEqual(len(result["results"]), 1)
        paper = result["results"][0]
        self.assertEqual(paper["scopus_id"], "123")
        self.assertEqual(paper["doi"], "10.1000/example")
        self.assertEqual(paper["cited_by_count"], 7)
        self.assertTrue(paper["open_access"])
        self.assertEqual(paper["scopus_url"], "https://scopus.example/123")
        self.assertEqual(result["quota"]["remaining"], 19999)

    def test_abstract_auto_detects_doi_and_normalizes_content(self):
        transport = FakeTransport(ABSTRACT_PAYLOAD)
        client = ElsevierClient("secret", transport=transport)
        result = client.get_abstract("https://doi.org/10.1000/example", identifier_type="auto", view="FULL")

        parsed = urlparse(transport.calls[0]["url"])
        self.assertEqual(parsed.path, "/content/abstract/doi/10.1000/example")
        self.assertEqual(parse_qs(parsed.query)["view"], ["FULL"])
        self.assertEqual(result["paper"]["abstract"], "We rank candidate resumes against job descriptions.")
        self.assertEqual(result["paper"]["authors"][0]["author_id"], "111")
        self.assertEqual(result["paper"]["subject_areas"][0]["name"], "Computer Science")

    def test_identifier_detection(self):
        self.assertEqual(detect_identifier_type("10.1109/ACCESS.2025.123"), ("doi", "10.1109/ACCESS.2025.123"))
        self.assertEqual(detect_identifier_type("2-s2.0-85123456789"), ("eid", "2-s2.0-85123456789"))
        self.assertEqual(detect_identifier_type("SCOPUS_ID:85123456789"), ("scopus_id", "85123456789"))
        self.assertEqual(detect_identifier_type("85123456789"), ("scopus_id", "85123456789"))

    def test_api_error_includes_actionable_entitlement_message(self):
        payload = {"service-error": {"status": {"statusCode": "AUTHORIZATION_ERROR", "statusText": "Insufficient privileges"}}}
        client = ElsevierClient("bad", transport=FakeTransport(payload, status=401))
        with self.assertRaises(ElsevierAPIError) as ctx:
            client.search("ALL(test)")
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("institution", str(ctx.exception).lower())


SCHOLAR_PAYLOAD = {
    "search_metadata": {"status": "Success"},
    "search_information": {"total_results": 12345},
    "organic_results": [
        {
            "position": 1,
            "result_id": "abc123",
            "title": "AI Resume Screening with Transformers",
            "link": "https://example.org/paper",
            "snippet": "This paper ranks resumes against job descriptions.",
            "publication_info": {
                "summary": "R Firdaus, A Researcher - Example Journal, 2025",
                "authors": [{"name": "R Firdaus", "author_id": "author1", "link": "https://scholar.google.com/citations?user=author1"}],
            },
            "inline_links": {
                "cited_by": {"total": 17, "link": "https://scholar.google.com/scholar?cites=abc"},
                "related_pages_link": "https://scholar.google.com/scholar?q=related:abc",
                "versions": {"total": 3, "link": "https://scholar.google.com/scholar?cluster=abc"},
                "serpapi_cite_link": "https://serpapi.com/search?engine=google_scholar_cite&q=abc",
            },
            "resources": [{"title": "PDF", "file_format": "PDF", "link": "https://example.org/paper.pdf"}],
        }
    ],
}


class ScholarClientTests(unittest.TestCase):
    def test_scholar_search_normalizes_results_and_filters_year(self):
        transport = FakeTransport(SCHOLAR_PAYLOAD)
        client = GoogleScholarClient("serp-secret", transport=transport)
        result = client.search("AI resume screening", limit=20, start=10, year_from=2020, year_to=2026, language="id")

        call = transport.calls[0]
        params = parse_qs(urlparse(call["url"]).query)
        self.assertEqual(params["engine"], ["google_scholar"])
        self.assertEqual(params["q"], ["AI resume screening"])
        self.assertEqual(params["num"], ["20"])
        self.assertEqual(params["start"], ["10"])
        self.assertEqual(params["as_ylo"], ["2020"])
        self.assertEqual(params["as_yhi"], ["2026"])
        self.assertEqual(params["hl"], ["id"])
        paper = result["results"][0]
        self.assertEqual(paper["title"], "AI Resume Screening with Transformers")
        self.assertEqual(paper["cited_by_count"], 17)
        self.assertEqual(paper["authors"][0]["author_id"], "author1")
        self.assertEqual(paper["pdf_url"], "https://example.org/paper.pdf")

    def test_scholar_handler_reports_missing_key(self):
        previous = os.environ.pop("SERPAPI_API_KEY", None)
        try:
            result = json.loads(handle_google_scholar_search({"query": "resume screening"}))
            self.assertFalse(result["success"])
            self.assertIn("SERPAPI_API_KEY", result["error"])
        finally:
            if previous is not None:
                os.environ["SERPAPI_API_KEY"] = previous


class HandlerTests(unittest.TestCase):
    def setUp(self):
        self.old_key = os.environ.pop("ELSEVIER_API_KEY", None)

    def tearDown(self):
        if self.old_key is not None:
            os.environ["ELSEVIER_API_KEY"] = self.old_key
        else:
            os.environ.pop("ELSEVIER_API_KEY", None)

    def test_search_handler_reports_missing_key_without_crashing(self):
        result = json.loads(handle_scopus_search({"query": "ALL(test)"}))
        self.assertFalse(result["success"])
        self.assertIn("ELSEVIER_API_KEY", result["error"])

    def test_abstract_handler_validates_identifier(self):
        result = json.loads(handle_scopus_abstract({"identifier": ""}))
        self.assertFalse(result["success"])
        self.assertIn("identifier", result["error"].lower())


if __name__ == "__main__":
    unittest.main()
