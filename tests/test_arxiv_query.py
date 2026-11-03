from urllib.parse import parse_qs, urlparse

import pytest

from academic_research.providers.arxiv import ArxivProvider, _build_arxiv_query

EMPTY_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>0</opensearch:totalResults>
  <opensearch:startIndex>0</opensearch:startIndex>
</feed>"""

ONE_RESULT_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>1</opensearch:totalResults>
  <opensearch:startIndex>0</opensearch:startIndex>
  <entry>
    <id>http://arxiv.org/abs/2501.00001v1</id>
    <published>2025-01-01T00:00:00Z</published>
    <title>Synthetic Vehicle Counting Record</title>
  </entry>
</feed>"""


class SequenceTransport:
    def __init__(self, *bodies):
        self.bodies = list(bodies)
        self.calls = []

    def __call__(self, url, headers, timeout):
        self.calls.append({"url": url, "headers": headers, "timeout": timeout})
        return 200, {}, self.bodies[min(len(self.calls), len(self.bodies)) - 1]

    def params(self, index=0):
        return parse_qs(urlparse(self.calls[index]["url"]).query)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "vehicle counting YOLO ByteTrack",
            "all:vehicle AND all:counting AND all:YOLO AND all:ByteTrack",
        ),
        ('"traffic volume" estimation', 'all:"traffic volume" AND all:estimation'),
        ('detection "object tracking"', 'all:detection AND all:"object tracking"'),
        ('"object tracking"', 'all:"object tracking"'),
        ("  yolo    tracking  ", "all:yolo AND all:tracking"),
        ('yolo "" tracking "  "', "all:yolo AND all:tracking"),
        ("transformer", "all:transformer"),
    ],
)
def test_build_arxiv_query_joins_plain_terms_with_and(raw, expected):
    assert _build_arxiv_query(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "ti:yolo AND abs:traffic",
        'ti:"vision transformer" AND cat:cs.IR',
        "au:smith",
        "cat:cs.CV",
        "all:research",
        "yolo OR detr",
        "tracking ANDNOT survey",
        "(yolo detr) tracking",
    ],
)
def test_build_arxiv_query_preserves_explicit_arxiv_syntax(raw):
    assert _build_arxiv_query(raw) == raw


def test_arxiv_search_sends_built_query_url_encoded():
    transport = SequenceTransport(ONE_RESULT_FEED)

    result = ArxivProvider(transport=transport).search('"traffic volume" estimation', limit=5)

    raw_query = urlparse(transport.calls[0]["url"]).query
    assert "search_query=all%3A%22traffic+volume%22+AND+all%3Aestimation" in raw_query
    assert transport.params()["search_query"] == ['all:"traffic volume" AND all:estimation']
    assert result.query == '"traffic volume" estimation'
    assert result.metadata["search_query"] == 'all:"traffic volume" AND all:estimation'
    assert result.warnings == []


def test_arxiv_id_lookup_path_is_unchanged():
    transport = SequenceTransport(ONE_RESULT_FEED)

    ArxivProvider(transport=transport).search(ids=["2501.00001", "2401.00002v2"])

    params = transport.params()
    assert params["id_list"] == ["2501.00001,2401.00002v2"]
    assert "search_query" not in params
    assert len(transport.calls) == 1


def test_arxiv_falls_back_to_any_term_with_warning_when_all_terms_match_nothing():
    transport = SequenceTransport(EMPTY_FEED, ONE_RESULT_FEED)

    result = ArxivProvider(transport=transport).search(
        "vehicle counting YOLO ByteTrack", limit=5
    )

    assert len(transport.calls) == 2
    assert transport.params(0)["search_query"] == [
        "all:vehicle AND all:counting AND all:YOLO AND all:ByteTrack"
    ]
    or_query = "all:vehicle OR all:counting OR all:YOLO OR all:ByteTrack"
    assert transport.params(1)["search_query"] == [or_query]
    assert result.total == 1
    assert [paper.title for paper in result.papers] == ["Synthetic Vehicle Counting Record"]
    assert result.query == "vehicle counting YOLO ByteTrack"
    assert result.metadata["search_query"] == or_query
    assert result.metadata["query_fallback"] == "any_term"
    assert len(result.warnings) == 1
    assert "OR" in result.warnings[0]


@pytest.mark.parametrize(
    ("query", "start"),
    [
        ("ti:yolo AND abs:traffic", 0),
        ("transformer", 0),
        ("vehicle counting", 10),
    ],
)
def test_arxiv_does_not_fall_back_for_explicit_syntax_single_terms_or_later_pages(
    query, start
):
    transport = SequenceTransport(EMPTY_FEED, ONE_RESULT_FEED)

    result = ArxivProvider(transport=transport).search(query, start=start)

    assert len(transport.calls) == 1
    assert result.total == 0
    assert result.warnings == []
    assert "query_fallback" not in result.metadata
