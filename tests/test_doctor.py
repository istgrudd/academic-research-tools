import json

from academic_research.credentials import CredentialResolver
from academic_research.doctor import doctor_report


def test_doctor_reports_first_search_ready_without_optional_credentials(tmp_path):
    resolver = CredentialResolver(config_path=tmp_path / "credentials.json", environ={})

    report = doctor_report(resolver=resolver)

    assert report["success"] is True
    assert report["ready_for_search"] is True
    assert report["credentials"]["configured_count"] == 0
    assert report["onboarding"]["configuration_required"] is False
    assert report["onboarding"]["optional_command"] == "academic-research configure"
    assert report["providers"]["arxiv"]["available"] is True


def test_doctor_reports_corrupt_config_without_leaking_contents(tmp_path):
    config_path = tmp_path / "credentials.json"
    config_path.write_text('{"credentials":{"ELSEVIER_API_KEY":"secret-in-corrupt-file"')
    config_path.chmod(0o600)
    resolver = CredentialResolver(config_path=config_path, environ={})

    report = doctor_report(resolver=resolver)

    serialized = json.dumps(report)
    assert report["success"] is False
    assert report["credentials"]["config_valid"] is False
    assert "secret-in-corrupt-file" not in serialized


def test_doctor_ignores_any_fixed_fallback_file_when_config_is_invalid(tmp_path):
    config_path = tmp_path / "credentials.json"
    config_path.write_text("invalid-primary")
    config_path.chmod(0o600)
    stale_fallback = tmp_path / ".ignored-invalid-config"
    stale_fallback.write_text("invalid-fallback")
    stale_fallback.chmod(0o600)

    report = doctor_report(
        resolver=CredentialResolver(config_path=config_path, environ={})
    )

    assert report["success"] is False
    assert report["ready_for_search"] is True
    assert report["credentials"]["config_valid"] is False
