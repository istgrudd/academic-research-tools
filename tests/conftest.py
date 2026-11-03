import pytest


@pytest.fixture(autouse=True)
def retry_sleeps(monkeypatch):
    """Record retry backoff delays instead of sleeping during tests."""
    delays = []
    monkeypatch.setattr("academic_research.providers._http._sleep", delays.append)
    return delays
