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


def sent_queries(transport):
    return [transport.params(index)["search_query"][0] for index in range(len(transport.calls))]


def test_arxiv_drops_trailing_term_before_any_term_fallback():
    transport = SequenceTransport(EMPTY_FEED, ONE_RESULT_FEED)

    result = ArxivProvider(transport=transport).search(
        "vehicle counting YOLO ByteTrack", limit=5
    )

    relaxed = "all:vehicle AND all:counting AND all:YOLO"
    assert sent_queries(transport) == [
        "all:vehicle AND all:counting AND all:YOLO AND all:ByteTrack",
        relaxed,
    ]
    assert result.total == 1
    assert result.query == "vehicle counting YOLO ByteTrack"
    assert result.metadata["search_query"] == relaxed
    assert result.metadata["query_fallback"] == "dropped_terms"
    assert result.metadata["dropped_terms"] == ["ByteTrack"]
    assert len(result.warnings) == 1
    assert "ByteTrack" in result.warnings[0]


def test_arxiv_drops_at_most_two_terms_and_keeps_at_least_two():
    transport = SequenceTransport(EMPTY_FEED, EMPTY_FEED, ONE_RESULT_FEED)

    result = ArxivProvider(transport=transport).search("vehicle counting YOLO ByteTrack")

    assert sent_queries(transport)[1:] == [
        "all:vehicle AND all:counting AND all:YOLO",
        "all:vehicle AND all:counting",
    ]
    assert result.metadata["dropped_terms"] == ["YOLO", "ByteTrack"]

    long_query = SequenceTransport(EMPTY_FEED)
    ArxivProvider(transport=long_query).search("a b c d e f")
    assert sent_queries(long_query)[1:] == [
        "all:a AND all:b AND all:c AND all:d AND all:e",
        "all:a AND all:b AND all:c AND all:d",
        "all:a OR all:b OR all:c OR all:d OR all:e OR all:f",
    ]


def test_arxiv_two_term_query_goes_straight_to_any_term_fallback():
    transport = SequenceTransport(EMPTY_FEED, ONE_RESULT_FEED)

    result = ArxivProvider(transport=transport).search('vehicle "object tracking"')

    assert sent_queries(transport) == [
        'all:vehicle AND all:"object tracking"',
        'all:vehicle OR all:"object tracking"',
    ]
    assert result.metadata["query_fallback"] == "any_term"


def test_arxiv_falls_back_to_any_term_with_warning_when_relaxed_queries_match_nothing():
    transport = SequenceTransport(EMPTY_FEED, EMPTY_FEED, EMPTY_FEED, ONE_RESULT_FEED)

    result = ArxivProvider(transport=transport).search(
        "vehicle counting YOLO ByteTrack", limit=5
    )

    or_query = "all:vehicle OR all:counting OR all:YOLO OR all:ByteTrack"
    assert sent_queries(transport) == [
        "all:vehicle AND all:counting AND all:YOLO AND all:ByteTrack",
        "all:vehicle AND all:counting AND all:YOLO",
        "all:vehicle AND all:counting",
        or_query,
    ]
    assert "dropped_terms" not in result.metadata
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
