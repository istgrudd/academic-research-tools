import http.client
import json
from urllib.error import URLError

import pytest

from academic_research import __version__
from academic_research.providers.arxiv import ArxivAPIError, ArxivProvider
from academic_research.providers.scopus import ScopusProvider
from academic_research.providers.semantic_scholar import (
    SemanticScholarAPIError,
    SemanticScholarProvider,
)
from academic_research.providers.serpapi_scholar import SerpAPIScholarProvider

S2_EMPTY = json.dumps({"total": 0, "offset": 0, "data": []}).encode()
ARXIV_EMPTY = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>0</opensearch:totalResults>
</feed>"""


class ScriptedTransport:
    """Replay exceptions or (status, body) responses in order."""

    def __init__(self, *steps):
        self.steps = list(steps)
        self.calls = []

    def __call__(self, url, headers, timeout):
        self.calls.append({"url": url, "headers": headers, "timeout": timeout})
        step = self.steps[min(len(self.calls), len(self.steps)) - 1]
        if isinstance(step, BaseException):
            raise step
        status, body = step
        return status, {}, body


NETWORK_FAILURES = [
    TimeoutError("timed out"),
    URLError(OSError(10060, "A connection attempt failed")),
    ConnectionResetError(10054, "An existing connection was forcibly closed"),
    http.client.RemoteDisconnected("Remote end closed connection"),
]


@pytest.mark.parametrize("failure", NETWORK_FAILURES, ids=type)
def test_semantic_scholar_retries_network_errors_with_backoff(failure, retry_sleeps):
    transport = ScriptedTransport(failure, failure, (200, S2_EMPTY))

    result = SemanticScholarProvider(transport=transport).search("traffic")

    assert result.total == 0
    assert len(transport.calls) == 3
    assert retry_sleeps == [1.0, 2.0]


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_semantic_scholar_retries_server_errors(status, retry_sleeps):
    transport = ScriptedTransport((status, b"{}"), (200, S2_EMPTY))

    SemanticScholarProvider(transport=transport).search("traffic")

    assert len(transport.calls) == 2
    assert retry_sleeps == [1.0]


def test_semantic_scholar_reports_rate_limit_after_exhausting_retries(retry_sleeps):
    transport = ScriptedTransport((429, json.dumps({"message": "Too Many Requests"}).encode()))

    with pytest.raises(SemanticScholarAPIError, match="Rate limit reached") as caught:
        SemanticScholarProvider(transport=transport).search("traffic")

    assert caught.value.status_code == 429
    assert len(transport.calls) == 3
    assert retry_sleeps == [1.0, 2.0]


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_semantic_scholar_does_not_retry_other_client_errors(status, retry_sleeps):
    transport = ScriptedTransport((status, json.dumps({"error": "bad request"}).encode()))

    with pytest.raises(SemanticScholarAPIError) as caught:
        SemanticScholarProvider(transport=transport).search("traffic")

    assert caught.value.status_code == status
    assert len(transport.calls) == 1
    assert retry_sleeps == []


def test_semantic_scholar_network_failure_explains_reachability(retry_sleeps):
    transport = ScriptedTransport(URLError(OSError(10060, "A connection attempt failed")))

    with pytest.raises(SemanticScholarAPIError) as caught:
        SemanticScholarProvider(transport=transport).search("traffic")

    message = str(caught.value)
    assert caught.value.status_code is None
    assert message.startswith("Network error while calling Semantic Scholar API")
    assert "10060" in message
    assert "api.semanticscholar.org" in message
    assert "firewall" in message
    assert "VPN" in message
    assert "HTTPS_PROXY" in message
    assert "3 attempts" in message
    assert len(transport.calls) == 3


def test_arxiv_retries_timeout_and_503_then_succeeds(retry_sleeps):
    transport = ScriptedTransport(TimeoutError("timed out"), (503, b""), (200, ARXIV_EMPTY))

    result = ArxivProvider(transport=transport).search("ti:traffic")

    assert result.total == 0
    assert len(transport.calls) == 3
    assert retry_sleeps == [1.0, 2.0]


def test_arxiv_does_not_retry_400(retry_sleeps):
    transport = ScriptedTransport((400, b"bad query"))

    with pytest.raises(ArxivAPIError, match="HTTP 400") as caught:
        ArxivProvider(transport=transport).search("ti:traffic")

    assert caught.value.status_code == 400
    assert len(transport.calls) == 1
    assert retry_sleeps == []


def test_arxiv_network_failure_explains_reachability(retry_sleeps):
    transport = ScriptedTransport(TimeoutError("timed out"))

    with pytest.raises(ArxivAPIError) as caught:
        ArxivProvider(transport=transport).search("ti:traffic")

    message = str(caught.value)
    assert message.startswith("Network error while calling arXiv API")
    assert "export.arxiv.org" in message
    assert "HTTPS_PROXY" in message
    assert len(transport.calls) == 3


def test_retries_can_be_disabled_for_single_request_checks(retry_sleeps):
    s2 = ScriptedTransport(TimeoutError("timed out"))
    arxiv = ScriptedTransport((503, b""))

    with pytest.raises(SemanticScholarAPIError):
        SemanticScholarProvider(transport=s2, max_retries=0).search("traffic")
    with pytest.raises(ArxivAPIError):
        ArxivProvider(transport=arxiv, max_retries=0).search("ti:traffic")

    assert len(s2.calls) == 1
    assert len(arxiv.calls) == 1
    assert retry_sleeps == []


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("45", 45.0),
        ("2.5", 2.5),
        ("500", 120.0),
        ("0", 1.0),
        ("-3", 1.0),
        ("not-a-number", 30.0),
        ("", 30.0),
    ],
)
def test_timeout_environment_variable_is_clamped(monkeypatch, value, expected):
    monkeypatch.setenv("ACADEMIC_RESEARCH_TIMEOUT", value)
    transport = ScriptedTransport((200, S2_EMPTY))

    SemanticScholarProvider(transport=transport).search("traffic")

    assert transport.calls[0]["timeout"] == expected
    assert ArxivProvider().timeout == expected
    assert ScopusProvider("synthetic-key").timeout == expected
    assert SerpAPIScholarProvider("synthetic-key").timeout == expected


def test_timeout_defaults_to_thirty_seconds(monkeypatch):
    monkeypatch.delenv("ACADEMIC_RESEARCH_TIMEOUT", raising=False)

    assert ArxivProvider().timeout == 30.0
    assert SemanticScholarProvider().timeout == 30.0


def test_explicit_timeout_overrides_environment(monkeypatch):
    monkeypatch.setenv("ACADEMIC_RESEARCH_TIMEOUT", "45")

    assert ArxivProvider(timeout=10).timeout == 10.0
    assert SemanticScholarProvider(timeout=500).timeout == 120.0


def test_user_agents_identify_current_release_without_placeholders():
    arxiv = ScriptedTransport((200, ARXIV_EMPTY))
    s2 = ScriptedTransport((200, S2_EMPTY))

    ArxivProvider(transport=arxiv).search("ti:traffic")
    SemanticScholarProvider(transport=s2).search("traffic")

    for transport in (arxiv, s2):
        agent = transport.calls[0]["headers"]["User-Agent"]
        assert f"/{__version__}" in agent
        assert "OWNER" not in agent
        assert "github.com/istgrudd/academic-research-tools" in agent
