from __future__ import annotations

from backend.runtime_paths import resource_root


def _script(name: str) -> str:
    return (
        resource_root()
        / "scripts"
        / name
    ).read_text(encoding="utf-8")


def test_scientific_collection_wrappers_do_not_expose_clear_identifier_switch():
    for name in (
        "collect_windows_normal_session.ps1",
        "collect_windows_controlled_attack.ps1",
    ):
        text = _script(name)
        assert "IncludeIdentifiers" not in text
        assert "--include-identifiers" not in text


def test_wifi_diagnostic_is_redacted_by_default_and_clear_ids_are_explicit_opt_in():
    text = _script("run_windows_wifi_diagnostic.ps1")
    assert "[switch]$IncludeIdentifiers" in text
    assert "if (-not $IncludeIdentifiers)" in text
    assert '"--redact-identifiers"' in text


def test_operational_scripts_resolve_project_root_before_python_or_alembic_work():
    for name in (
        "run_backend.ps1",
        "migrate_database.ps1",
        "collect_windows_normal_session.ps1",
        "collect_windows_controlled_attack.ps1",
        "run_windows_desktop_normal_pipeline.ps1",
        "run_windows_attack_evaluation_pipeline.ps1",
        "run_windows_full_scientific_pipeline.ps1",
        "check_windows_collection_readiness.ps1",
    ):
        text = _script(name)
        assert "$ProjectRoot = Split-Path -Parent $PSScriptRoot" in text
        assert "Set-Location $ProjectRoot" in text


def test_windows_collection_scripts_use_shared_host_guard():
    for name in (
        "collect_windows_normal_session.ps1",
        "collect_windows_controlled_attack.ps1",
        "run_windows_wifi_diagnostic.ps1",
        "check_windows_collection_readiness.ps1",
        "run_windows_desktop_normal_pipeline.ps1",
        "run_windows_attack_evaluation_pipeline.ps1",
        "run_windows_full_scientific_pipeline.ps1",
    ):
        text = _script(name)
        assert "powershell_compat.ps1" in text
        assert "Assert-EvilTwinWindowsHost" in text


def test_final_and_post_collection_pipelines_never_collect_wifi_implicitly():
    for name in (
        "run_final_end_to_end_windows.ps1",
        "run_windows_full_scientific_pipeline.ps1",
        "run_windows_attack_evaluation_pipeline.ps1",
    ):
        text = _script(name)
        assert "collect_windows_normal_session.ps1" not in text
        assert "collect_windows_controlled_attack.ps1" not in text
