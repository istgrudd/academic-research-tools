import asyncio
import json

from academic_research.credentials import CredentialResolver
from academic_research.hermes_plugin import register


class FakeContext:
    def __init__(self):
        self.tools = []
        self.skills = []

    def register_tool(self, **kwargs):
        self.tools.append(kwargs)

    def register_skill(self, *args):
        self.skills.append(args)


def test_hermes_adapter_registers_same_public_surface(monkeypatch, tmp_path):
    monkeypatch.setenv("ACADEMIC_RESEARCH_CONFIG_DIR", str(tmp_path))
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


def test_hermes_status_handler_returns_json_without_secret(monkeypatch, tmp_path):
    monkeypatch.setenv("ACADEMIC_RESEARCH_CONFIG_DIR", str(tmp_path))
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


def test_hermes_checks_saved_user_config_without_exposing_secret(monkeypatch, tmp_path):
    monkeypatch.setenv("ACADEMIC_RESEARCH_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("ELSEVIER_API_KEY", raising=False)
    CredentialResolver().set("ELSEVIER_API_KEY", "saved-hermes-secret")
    context = FakeContext()

    register(context)

    scopus_tool = next(tool for tool in context.tools if tool["name"] == "search_scopus")
    assert scopus_tool["check_fn"]() is True


def test_hermes_credential_checks_fail_closed_for_invalid_config(monkeypatch, tmp_path):
    monkeypatch.setenv("ACADEMIC_RESEARCH_CONFIG_DIR", str(tmp_path))
    for name in (
        "SEMANTIC_SCHOLAR_API_KEY",
        "ELSEVIER_API_KEY",
        "ELSEVIER_INST_TOKEN",
        "SERPAPI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    config_path = tmp_path / "credentials.json"
    config_path.write_text("invalid")
    config_path.chmod(0o600)
    context = FakeContext()

    register(context)

    tools = {tool["name"]: tool for tool in context.tools}
    assert tools["search_scopus"]["check_fn"]() is False
    payload = json.loads(tools["research_provider_status"]["handler"]({}))
    assert payload["success"] is False
    assert payload["doctor_command"] == "academic-research doctor"
