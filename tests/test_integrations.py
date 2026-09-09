import os
import stat
import traceback

import pytest

from academic_research.integrations import IntegrationError, install_platform


class Completed:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_claude_code_installer_uses_official_cli_and_installs_skill(tmp_path):
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return Completed(stdout="Added MCP server")

    result = install_platform(
        "claude-code",
        home=tmp_path,
        launcher=["uvx", "--from", "academic-research-tools", "academic-research", "serve"],
        executable="/usr/local/bin/claude",
        run=run,
    )

    assert calls[0][0] == [
        "/usr/local/bin/claude",
        "mcp",
        "add",
        "--scope",
        "user",
        "--transport",
        "stdio",
        "academic-research",
        "--",
        "uvx",
        "--from",
        "academic-research-tools",
        "academic-research",
        "serve",
    ]
    skill = tmp_path / ".claude/skills/academic-research-workflow/SKILL.md"
    assert skill.is_file()
    assert "Progressive onboarding" in skill.read_text()
    assert result["configured"] is True
    assert result["credentials_requested"] is False


def test_codex_installer_uses_official_cli_without_credentials(tmp_path):
    calls = []
    result_path = tmp_path / ".agents/skills/academic-research-workflow/SKILL.md"
    result_path.parent.mkdir(parents=True)
    if os.name != "nt":
        result_path.parent.chmod(0o755)

    def run(argv, **kwargs):
        calls.append(argv)
        return Completed(stdout="Added MCP server")

    result = install_platform(
        "codex",
        home=tmp_path,
        launcher=["academic-research", "serve"],
        executable="/usr/local/bin/codex",
        run=run,
    )

    assert calls == [
        [
            "/usr/local/bin/codex",
            "mcp",
            "add",
            "academic-research",
            "--",
            "academic-research",
            "serve",
        ]
    ]
    result_path = tmp_path / ".agents/skills/academic-research-workflow/SKILL.md"
    assert result_path.is_file()
    assert result["credentials_requested"] is False
    assert all("configure" not in argument for argument in calls[0])
    if os.name != "nt":
        assert stat.S_IMODE(result_path.parent.stat().st_mode) == 0o700


def test_installer_fails_cleanly_when_host_cli_is_missing(tmp_path):
    with pytest.raises(IntegrationError, match="Claude Code CLI was not found"):
        install_platform(
            "claude-code",
            home=tmp_path,
            launcher=["academic-research", "serve"],
            executable=None,
        )


def test_installer_treats_existing_registration_as_idempotent(tmp_path):
    def run(argv, **kwargs):
        return Completed(returncode=1, stderr="MCP server academic-research already exists")

    result = install_platform(
        "codex",
        home=tmp_path,
        launcher=["academic-research", "serve"],
        executable="/usr/local/bin/codex",
        run=run,
    )

    assert result["configured"] is True
    assert result["registration"] == "already_configured"
    assert (
        tmp_path / ".agents/skills/academic-research-workflow/SKILL.md"
    ).is_file()


def test_installer_does_not_echo_host_error_output(tmp_path):
    def run(argv, **kwargs):
        return Completed(returncode=1, stderr="host failure contained secret-value")

    with pytest.raises(IntegrationError) as error:
        install_platform(
            "codex",
            home=tmp_path,
            launcher=["academic-research", "serve"],
            executable="/usr/local/bin/codex",
            run=run,
        )

    assert "secret-value" not in str(error.value)


def test_installer_sanitizes_host_startup_failures(tmp_path):
    def run(argv, **kwargs):
        raise FileNotFoundError("startup failure contained secret-value")

    with pytest.raises(IntegrationError) as error:
        install_platform(
            "codex",
            home=tmp_path,
            launcher=["academic-research", "serve"],
            executable="/usr/local/bin/codex",
            run=run,
        )

    assert "secret-value" not in str(error.value)
    formatted = "".join(traceback.format_exception(error.value))
    assert "secret-value" not in formatted
