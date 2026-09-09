"""Host integrations for MCP-capable coding agents."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from importlib.resources import files
from pathlib import Path
from typing import Any

_SERVER_NAME = "academic-research"
_SUPPORTED_PLATFORMS = {"claude-code", "codex"}


class IntegrationError(RuntimeError):
    """Raised when a host integration cannot be installed safely."""


def default_launcher() -> list[str]:
    """Return a durable local MCP launcher without embedding credentials."""
    if shutil.which("uvx"):
        return [
            "uvx",
            "--from",
            "academic-research-tools",
            "academic-research",
            "serve",
        ]
    executable = shutil.which("academic-research")
    if executable:
        return [executable, "serve"]
    return [sys.executable, "-m", "academic_research.cli", "serve"]


def _host_command(platform: str, executable: str, launcher: Sequence[str]) -> list[str]:
    if platform == "claude-code":
        return [
            executable,
            "mcp",
            "add",
            "--scope",
            "user",
            "--transport",
            "stdio",
            _SERVER_NAME,
            "--",
            *launcher,
        ]
    if platform == "codex":
        return [executable, "mcp", "add", _SERVER_NAME, "--", *launcher]
    raise IntegrationError(f"Unsupported platform: {platform}")


def _skill_destination(platform: str, home: Path) -> Path:
    root = ".claude" if platform == "claude-code" else ".agents"
    return home / root / "skills" / "academic-research-workflow" / "SKILL.md"


def _install_skill(platform: str, home: Path) -> Path:
    source = (
        files("academic_research")
        .joinpath("skills")
        .joinpath("academic-research-workflow")
        .joinpath("SKILL.md")
    )
    destination = _skill_destination(platform, home)
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != "nt":
        destination.parent.chmod(0o700)
    destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    destination.chmod(0o600)
    return destination


def install_platform(
    platform: str,
    *,
    home: Path | None = None,
    launcher: Sequence[str] | None = None,
    executable: str | None = None,
    run: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    """Register the stdio MCP server and workflow skill for one host."""
    if platform not in _SUPPORTED_PLATFORMS:
        raise IntegrationError(f"Unsupported platform: {platform}")
    host_name = "Claude Code" if platform == "claude-code" else "Codex"
    host_command = "claude" if platform == "claude-code" else "codex"
    host_executable = executable or shutil.which(host_command)
    if not host_executable:
        raise IntegrationError(f"{host_name} CLI was not found on PATH")

    selected_launcher = list(launcher or default_launcher())
    command = _host_command(platform, host_executable, selected_launcher)
    try:
        completed = run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        raise IntegrationError(
            f"{host_name} CLI could not be executed; host diagnostics were suppressed"
        ) from None
    registration = "added"
    if completed.returncode != 0:
        host_output = f"{completed.stderr or ''}\n{completed.stdout or ''}".lower()
        if "already exists" in host_output or "already configured" in host_output:
            registration = "already_configured"
        else:
            raise IntegrationError(
                f"{host_name} MCP registration failed with exit code "
                f"{completed.returncode}; host output was suppressed to protect secrets"
            )

    try:
        skill_path = _install_skill(platform, Path(home or Path.home()))
    except OSError:
        raise IntegrationError(
            f"{host_name} MCP registration is ready, but its workflow skill "
            "could not be installed"
        ) from None
    return {
        "platform": platform,
        "configured": True,
        "registration": registration,
        "server": _SERVER_NAME,
        "launcher": selected_launcher,
        "skill_path": str(skill_path),
        "credentials_requested": False,
    }
