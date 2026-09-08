import asyncio
import json

from academic_research.hermes_plugin import register


class FakeContext:
    def __init__(self):
        self.tools = []
        self.skills = []

    def register_tool(self, **kwargs):
        self.tools.append(kwargs)

    def register_skill(self, *args):
        self.skills.append(args)


def test_hermes_adapter_registers_same_public_surface(monkeypatch):
    monkeypatch.delenv("ELSEVIER_API_KEY", raising=False)
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    context = FakeContext()

    register(context)

    tools = {tool["name"]: tool for tool in context.tools}
    assert set(tools) == {
        "research_provider_status",
        "search_papers",
        "search_arxiv",
        "search_semantic_scholar",
        "search_scopus",
        "get_scopus_abstract",
        "search_scopus_authors",
        "search_google_scholar",
    }
    assert tools["search_scopus"]["check_fn"]() is False
    assert tools["get_scopus_abstract"]["check_fn"]() is False
    assert tools["search_google_scholar"]["check_fn"]() is False
    assert len(context.skills) == 1


def test_hermes_status_handler_returns_json_without_secret(monkeypatch):
    monkeypatch.setenv("ELSEVIER_API_KEY", "never-print-this-key")
    context = FakeContext()
    register(context)
    status_tool = next(
        tool for tool in context.tools if tool["name"] == "research_provider_status"
    )

    payload = json.loads(status_tool["handler"]({}))

    assert payload["success"] is True
    assert payload["providers"]["scopus"]["available"] is True
    assert "never-print-this-key" not in json.dumps(payload)


def test_hermes_sync_handler_is_safe_inside_running_event_loop():
    context = FakeContext()
    register(context)
    status_handler = next(
        tool["handler"]
        for tool in context.tools
        if tool["name"] == "research_provider_status"
    )

    async def invoke_from_async_host():
        return status_handler({})

    payload = json.loads(asyncio.run(invoke_from_async_host()))
    assert payload["success"] is True
