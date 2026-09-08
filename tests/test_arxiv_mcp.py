import asyncio
import json
from urllib.parse import parse_qs, urlparse

import pytest

from academic_research.mcp_server import ResearchTools, create_server
from academic_research.providers.arxiv import ArxivProvider

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
    <title>  Vision   Transformer\n for Research </title>
    <summary> We study evidence-grounded academic discovery. </summary>
    <author>
      <name>Rudi Firdaus</name>
      <arxiv:affiliation>Telkom University</arxiv:affiliation>
    </author>
    <category term="cs.IR" scheme="http://arxiv.org/schemas/atom"/>
    <arxiv:primary_category term="cs.IR"/>
    <arxiv:doi>10.1000/example</arxiv:doi>
    <link href="https://arxiv.org/abs/2501.12345v2" rel="alternate" type="text/html"/>
    <link href="https://arxiv.org/pdf/2501.12345v2" rel="related" type="application/pdf"/>
  </entry>
</feed>'''


class FakeTransport:
    def __init__(self, body: bytes = ARXIV_XML, status: int = 200):
        self.body = body
        self.status = status
        self.calls = []

    def __call__(self, url, headers, timeout):
        self.calls.append({"url": url, "headers": headers, "timeout": timeout})
        return self.status, {}, self.body


def test_arxiv_provider_returns_normalized_search_result():
    transport = FakeTransport()
    provider = ArxivProvider(transport=transport)

    result = provider.search(
        'ti:"vision transformer" AND cat:cs.IR',
        limit=1,
        start=5,
        sort_by="submittedDate",
    )

    params = parse_qs(urlparse(transport.calls[0]["url"]).query)
    assert params["search_query"] == ['ti:"vision transformer" AND cat:cs.IR']
    assert params["start"] == ["5"]
    assert params["max_results"] == ["1"]

    assert result.source == "arxiv"
    assert result.total == 42
    assert result.next_offset == 6
    paper = result.papers[0]
    assert paper.title == "Vision Transformer for Research"
    assert paper.abstract == "We study evidence-grounded academic discovery."
    assert paper.doi == "10.1000/example"
    assert paper.source_ids == {"arxiv": "2501.12345v2"}
    assert paper.authors[0].name == "Rudi Firdaus"
    assert paper.authors[0].affiliation == "Telkom University"
    assert paper.primary_url == "https://arxiv.org/abs/2501.12345v2"
    assert paper.pdf_url == "https://arxiv.org/pdf/2501.12345v2"


def test_research_tools_exposes_arxiv_result_as_json_safe_dict():
    tools = ResearchTools(arxiv=ArxivProvider(transport=FakeTransport()))

    payload = asyncio.run(
        tools.search_arxiv(
            query="all:research",
            limit=1,
            start=0,
            sort_by="relevance",
            sort_order="descending",
        )
    )

    assert payload["success"] is True
    assert payload["source"] == "arxiv"
    assert payload["results"][0]["source"] == "arxiv"
    assert payload["results"][0]["title"] == "Vision Transformer for Research"
    json.dumps(payload)


def test_arxiv_rejects_empty_query_and_ids():
    provider = ArxivProvider(transport=FakeTransport())
    with pytest.raises(ValueError, match="query or ids is required"):
        provider.search()


def test_mcp_server_registers_and_calls_arxiv_tool():
    async def exercise():
        server = create_server(
            tools=ResearchTools(arxiv=ArxivProvider(transport=FakeTransport()))
        )
        registered = await server.list_tools()
        assert {tool.name for tool in registered} == {"search_arxiv"}

        response = await server.call_tool(
            "search_arxiv", {"query": "all:research", "limit": 1}
        )
        assert response.is_error is False
        payload = json.loads(response.content[0].text)
        assert payload["success"] is True
        assert payload["results"][0]["source"] == "arxiv"

    asyncio.run(exercise())
