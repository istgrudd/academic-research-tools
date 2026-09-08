import json
import sys
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PLUGIN_PARENT = Path(__file__).resolve().parents[2]
if str(PLUGIN_PARENT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_PARENT))

from scopus_research.arxiv_client import ArxivClient
from scopus_research.semantic_scholar_client import SemanticScholarClient
from scopus_research.tools import handle_arxiv_search, handle_semantic_scholar_search

ARXIV_XML = b'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <opensearch:totalResults>42</opensearch:totalResults>
  <opensearch:startIndex>5</opensearch:startIndex>
  <opensearch:itemsPerPage>1</opensearch:itemsPerPage>
  <entry>
    <id>http://arxiv.org/abs/2501.12345v2</id>
    <updated>2025-02-02T00:00:00Z</updated>
    <published>2025-01-01T00:00:00Z</published>
    <title>  Vision   Transformer\n for Recruitment </title>
    <summary> We study automated CV screening. </summary>
    <author><name>Rudi Firdaus</name><arxiv:affiliation>Telkom University</arxiv:affiliation></author>
    <category term="cs.CV" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.AI" scheme="http://arxiv.org/schemas/atom"/>
    <arxiv:primary_category term="cs.CV"/>
    <arxiv:doi>10.1000/example</arxiv:doi>
    <arxiv:journal_ref>Example Journal 1 (2025)</arxiv:journal_ref>
    <link href="https://arxiv.org/abs/2501.12345v2" rel="alternate" type="text/html"/>
    <link href="https://arxiv.org/pdf/2501.12345v2" rel="related" type="application/pdf"/>
  </entry>
</feed>'''

S2_PAYLOAD = {
    "total": 7,
    "offset": 0,
    "next": 1,
    "data": [{
        "paperId": "paper-1", "corpusId": 123, "externalIds": {"DOI": "10.1000/example", "ArXiv": "2501.12345"},
        "url": "https://www.semanticscholar.org/paper/paper-1", "title": "Vision Transformer for Recruitment",
        "abstract": "We study automated CV screening.", "venue": "ExampleConf", "year": 2025,
        "publicationDate": "2025-01-01", "authors": [{"authorId": "a1", "name": "Rudi Firdaus"}],
        "citationCount": 11, "influentialCitationCount": 2, "referenceCount": 30, "isOpenAccess": True,
        "openAccessPdf": {"url": "https://example.org/paper.pdf", "status": "GREEN", "license": "CCBY"},
        "fieldsOfStudy": ["Computer Science"], "s2FieldsOfStudy": [{"category": "Computer Science", "source": "s2-fos-model"}],
        "publicationTypes": ["JournalArticle"],
        "publicationVenue": {"id": "v1", "name": "Example Conference", "type": "conference"},
        "journal": {"name": "Example Journal", "volume": "1", "pages": "1-10"},
    }],
}


class FakeTransport:
    def __init__(self, body, status=200):
        self.body = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.status = status
        self.calls = []

    def __call__(self, url, headers, timeout):
        self.calls.append({"url": url, "headers": headers, "timeout": timeout})
        return self.status, {}, self.body


class ArxivTests(unittest.TestCase):
    def test_query_encoding_and_atom_normalization(self):
        transport = FakeTransport(ARXIV_XML)
        result = ArxivClient(transport=transport).search('ti:"vision transformer" AND cat:cs.CV', limit=1, start=5, sort_by="submittedDate")
        params = parse_qs(urlparse(transport.calls[0]["url"]).query)
        self.assertEqual(params["search_query"], ['ti:"vision transformer" AND cat:cs.CV'])
        self.assertEqual(params["start"], ["5"])
        self.assertEqual(params["max_results"], ["1"])
        self.assertIn("Hermes-Agent-Research", transport.calls[0]["headers"]["User-Agent"])
        paper = result["results"][0]
        self.assertEqual(paper["arxiv_id"], "2501.12345v2")
        self.assertEqual(paper["title"], "Vision Transformer for Recruitment")
        self.assertEqual(paper["authors"][0]["affiliation"], "Telkom University")
        self.assertEqual(paper["primary_category"], "cs.CV")
        self.assertEqual(paper["doi"], "10.1000/example")
        self.assertEqual(paper["pdf_url"], "https://arxiv.org/pdf/2501.12345v2")
        self.assertEqual(result["next_start"], 6)

    def test_ids_are_supported_and_limits_are_capped(self):
        transport = FakeTransport(ARXIV_XML)
        ArxivClient(transport=transport).search(ids=["2501.12345v2"], limit=999)
        params = parse_qs(urlparse(transport.calls[0]["url"]).query)
        self.assertEqual(params["id_list"], ["2501.12345v2"])
        self.assertEqual(params["max_results"], ["100"])

    def test_handler_requires_query_or_ids(self):
        payload = json.loads(handle_arxiv_search({}))
        self.assertFalse(payload["success"])


class SemanticScholarTests(unittest.TestCase):
    def test_search_encodes_filters_and_normalizes(self):
        transport = FakeTransport(S2_PAYLOAD)
        client = SemanticScholarClient("secret", transport=transport)
        result = client.search("vision transformer recruitment", limit=1, year="2020-2026")
        params = parse_qs(urlparse(transport.calls[0]["url"]).query)
        self.assertEqual(params["query"], ["vision transformer recruitment"])
        self.assertEqual(params["year"], ["2020-2026"])
        self.assertEqual(transport.calls[0]["headers"]["x-api-key"], "secret")
        paper = result["results"][0]
        self.assertEqual(paper["external_ids"]["ArXiv"], "2501.12345")
        self.assertEqual(paper["citation_count"], 11)
        self.assertEqual(paper["open_access_pdf"]["url"], "https://example.org/paper.pdf")
        self.assertEqual(result["next_offset"], 1)
        self.assertTrue(result["authenticated"])

    def test_key_is_optional(self):
        transport = FakeTransport(S2_PAYLOAD)
        result = SemanticScholarClient(transport=transport).search("test")
        self.assertNotIn("x-api-key", transport.calls[0]["headers"])
        self.assertFalse(result["authenticated"])

    def test_year_validation_and_handler_validation(self):
        with self.assertRaises(ValueError):
            SemanticScholarClient(transport=FakeTransport(S2_PAYLOAD)).search("test", year="recent")
        payload = json.loads(handle_semantic_scholar_search({}))
        self.assertFalse(payload["success"])


if __name__ == "__main__":
    unittest.main()
