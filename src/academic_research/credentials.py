"""Local credential resolution with environment-variable overrides."""

from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import quote_plus

CREDENTIAL_NAMES = frozenset(
    {
        "SEMANTIC_SCHOLAR_API_KEY",
        "ELSEVIER_API_KEY",
        "ELSEVIER_INST_TOKEN",
        "SERPAPI_API_KEY",
    }
)


class CredentialConfigError(ValueError):
    """Raised when the local credential configuration is invalid."""


def default_credentials_path() -> Path:
    """Return the user-scoped credential file path for the current platform."""
    override = os.environ.get("ACADEMIC_RESEARCH_CONFIG_DIR", "").strip()
    if override:
        return Path(override).expanduser() / "credentials.json"
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "academic-research" / "credentials.json"


class CredentialResolver:
    """Resolve provider credentials from environment or protected user config."""

    def __init__(
        self,
        *,
        config_path: str | Path | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self.config_path = Path(config_path) if config_path else default_credentials_path()
        self.environ = os.environ if environ is None else environ

    @staticmethod
    def _validate_name(name: str) -> str:
        if name not in CREDENTIAL_NAMES:
            raise CredentialConfigError(f"Unsupported credential name: {name}")
        return name

    def _load(self) -> dict[str, str]:
        if not self.config_path.exists():
            return {}
        if os.name != "nt":
            if stat.S_IMODE(self.config_path.parent.stat().st_mode) & 0o077:
                raise CredentialConfigError(
                    "Credential config directory permissions are too open: "
                    f"{self.config_path.parent}; set mode 0700"
                )
            if stat.S_IMODE(self.config_path.stat().st_mode) & 0o077:
                raise CredentialConfigError(
                    f"Credential config permissions are too open: {self.config_path}; "
                    "set mode 0600"
                )
        try:
            payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CredentialConfigError(
                f"Credential config could not be read: {self.config_path}"
            ) from exc
        if not isinstance(payload, dict) or payload.get("version") != 1:
            raise CredentialConfigError("Unsupported credential config format")
        credentials = payload.get("credentials", {})
        if not isinstance(credentials, dict):
            raise CredentialConfigError("Credential config entries must be an object")
        return {
            name: value.strip()
            for name, value in credentials.items()
            if name in CREDENTIAL_NAMES and isinstance(value, str) and value.strip()
        }

    def get(self, name: str) -> str | None:
        """Return one credential, preferring the current process environment."""
        name = self._validate_name(name)
        environment_value = str(self.environ.get(name, "")).strip()
        if environment_value:
            return environment_value
        return self._load().get(name)

    def source(self, name: str) -> str | None:
        """Report where a credential was found without exposing its value."""
        name = self._validate_name(name)
        if str(self.environ.get(name, "")).strip():
            return "environment"
        return "user_config" if self._load().get(name) else None

    def list_sources(self) -> dict[str, str | None]:
        """List credential sources without exposing credential values."""
        saved = self._load()
        return {
            name: (
                "environment"
                if str(self.environ.get(name, "")).strip()
                else "user_config"
                if saved.get(name)
                else None
            )
            for name in sorted(CREDENTIAL_NAMES)
        }

    def redact(self, text: str) -> str:
        """Remove configured credential values from diagnostic text."""
        rendered = str(text)
        try:
            saved = self._load()
        except CredentialConfigError:
            saved = {}
        values = {
            str(self.environ.get(name, "")).strip() or saved.get(name, "")
            for name in CREDENTIAL_NAMES
        }
        for value in sorted((item for item in values if item), key=len, reverse=True):
            rendered = rendered.replace(value, "[REDACTED]")
            rendered = rendered.replace(quote_plus(value), "[REDACTED]")
        return rendered

    def set(self, name: str, value: str) -> None:
        """Persist a credential in the protected user configuration."""
        name = self._validate_name(name)
        value = str(value).strip()
        if not value or "\n" in value or "\r" in value:
            raise CredentialConfigError("Credential value must be a non-empty single line")
        credentials = self._load()
        credentials[name] = value
        self._write(credentials)

    def remove(self, name: str) -> bool:
        """Remove a stored credential; environment variables are never modified."""
        name = self._validate_name(name)
        credentials = self._load()
        removed = credentials.pop(name, None) is not None
        if removed:
            self._write(credentials)
        return removed

    def _write(self, credentials: Mapping[str, str]) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if os.name != "nt":
            self.config_path.parent.chmod(0o700)
        payload = json.dumps(
            {"version": 1, "credentials": dict(credentials)},
            indent=2,
            sort_keys=True,
        )
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.config_path.parent,
                prefix=".credentials-",
                delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                if os.name != "nt":
                    temporary_path.chmod(0o600)
                handle.write(payload)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.config_path)
            if os.name != "nt":
                self.config_path.chmod(0o600)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
