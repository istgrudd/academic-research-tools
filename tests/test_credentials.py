import json
import os
import stat

import pytest

from academic_research.credentials import CredentialConfigError, CredentialResolver


def test_saved_credential_is_private_and_resolved_without_exposure(tmp_path, monkeypatch):
    monkeypatch.delenv("ELSEVIER_API_KEY", raising=False)
    config_path = tmp_path / "config" / "credentials.json"
    resolver = CredentialResolver(config_path=config_path)

    resolver.set("ELSEVIER_API_KEY", "local-secret")

    assert resolver.get("ELSEVIER_API_KEY") == "local-secret"
    assert resolver.source("ELSEVIER_API_KEY") == "user_config"
    if os.name != "nt":
        assert stat.S_IMODE(config_path.stat().st_mode) == 0o600
        assert stat.S_IMODE(config_path.parent.stat().st_mode) == 0o700
    assert json.loads(config_path.read_text())["version"] == 1


def test_environment_overrides_saved_credential(tmp_path):
    config_path = tmp_path / "credentials.json"
    resolver = CredentialResolver(
        config_path=config_path,
        environ={"ELSEVIER_API_KEY": "environment-secret"},
    )
    resolver.set("ELSEVIER_API_KEY", "saved-secret")

    assert resolver.get("ELSEVIER_API_KEY") == "environment-secret"
    assert resolver.source("ELSEVIER_API_KEY") == "environment"


def test_remove_only_deletes_saved_credential(tmp_path):
    resolver = CredentialResolver(config_path=tmp_path / "credentials.json", environ={})
    resolver.set("SERPAPI_API_KEY", "saved-secret")

    assert resolver.remove("SERPAPI_API_KEY") is True
    assert resolver.remove("SERPAPI_API_KEY") is False
    assert resolver.get("SERPAPI_API_KEY") is None


def test_corrupt_config_fails_without_rendering_file_contents(tmp_path):
    config_path = tmp_path / "credentials.json"
    config_path.write_text('{"secret": "do-not-render"')
    resolver = CredentialResolver(config_path=config_path, environ={})

    try:
        resolver.get("ELSEVIER_API_KEY")
    except ValueError as exc:
        assert "do-not-render" not in str(exc)
        assert str(config_path) in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("corrupt configuration should fail")


@pytest.mark.skipif(os.name == "nt", reason="Windows uses filesystem ACLs")
def test_insecure_unix_permissions_are_rejected_without_exposing_value(tmp_path):
    config_path = tmp_path / "credentials.json"
    config_path.write_text(
        json.dumps(
            {
                "version": 1,
                "credentials": {"ELSEVIER_API_KEY": "permission-secret"},
            }
        )
    )
    config_path.chmod(0o644)
    resolver = CredentialResolver(config_path=config_path, environ={})

    with pytest.raises(CredentialConfigError) as error:
        resolver.get("ELSEVIER_API_KEY")

    assert "0600" in str(error.value)
    assert "permission-secret" not in str(error.value)


@pytest.mark.skipif(os.name == "nt", reason="Windows uses filesystem ACLs")
def test_insecure_unix_config_directory_is_rejected(tmp_path):
    config_path = tmp_path / "config" / "credentials.json"
    resolver = CredentialResolver(config_path=config_path, environ={})
    resolver.set("ELSEVIER_API_KEY", "directory-permission-secret")
    config_path.parent.chmod(0o755)

    with pytest.raises(CredentialConfigError) as error:
        resolver.get("ELSEVIER_API_KEY")

    assert "0700" in str(error.value)
    assert "directory-permission-secret" not in str(error.value)


def test_redaction_removes_raw_and_url_encoded_credentials(tmp_path):
    resolver = CredentialResolver(config_path=tmp_path / "credentials.json", environ={})
    resolver.set("SERPAPI_API_KEY", "key/with space")

    rendered = resolver.redact("raw=key/with space&encoded=key%2Fwith+space")

    assert "key/with space" not in rendered
    assert "key%2Fwith+space" not in rendered
    assert rendered.count("[REDACTED]") == 2
