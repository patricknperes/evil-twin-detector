from __future__ import annotations

import json

from backend.runtime_paths import resource_root


def test_frontend_typecheck_uses_project_references_build_mode():
    root = resource_root()
    package = json.loads(
        (root / "frontend" / "package.json").read_text(encoding="utf-8")
    )
    assert package["scripts"]["typecheck"] == "tsc -b --force --pretty false"


def test_tsconfig_node_does_not_emit_transient_vite_config_js():
    root = resource_root()
    config = json.loads(
        (root / "frontend" / "tsconfig.node.json").read_text(encoding="utf-8")
    )
    assert config["compilerOptions"]["noEmit"] is True


def test_diagnostics_api_method_is_connected():
    root = resource_root()
    source = (root / "frontend" / "src" / "lib" / "api.ts").read_text(
        encoding="utf-8"
    )
    assert "diagnosticsSupportBundle" in source
    assert '"/diagnostics/support-bundle"' in source


def test_suspicion_badge_callers_use_level_prop():
    root = resource_root()
    src = root / "frontend" / "src"
    offenders = []
    for path in src.rglob("*.tsx"):
        text = path.read_text(encoding="utf-8")
        if "<SuspicionBadge value=" in text:
            offenders.append(str(path.relative_to(root)))
    assert offenders == []


def test_scan_in_progress_has_error_panel_mapping():
    root = resource_root()
    source = (
        root / "frontend" / "src" / "components" / "ScanErrorPanel.tsx"
    ).read_text(encoding="utf-8")
    assert "scan_in_progress:" in source


def test_network_observation_matches_backend_host_timestamp_contract():
    root = resource_root()
    source = (root / "frontend" / "src" / "types" / "api.ts").read_text(
        encoding="utf-8"
    )
    section = source.split("export interface NetworkObservation", 1)[1].split(
        "export interface ScanResponse", 1
    )[0]
    assert "host_timestamp_100ns: number;" in section
