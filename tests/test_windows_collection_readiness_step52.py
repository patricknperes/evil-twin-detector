from __future__ import annotations

import json

from desktop.implementation_freeze import compute_implementation_snapshot
from desktop.windows.collection_readiness import inspect_collection_readiness
from desktop.windows.wlanapi_ctypes import (
    NativeWifiInterface,
    NativeWifiInterfaceScan,
    NativeWifiScanBatch,
)


class ReadyScanner:
    def scan_all(self, **kwargs):
        interface = NativeWifiInterface(
            guid="GUID",
            description="Test Wi-Fi",
            state_code=1,
            state="connected",
            _guid_struct=None,
        )
        return NativeWifiScanBatch(
            negotiated_api_version=2,
            interface_scans=(
                NativeWifiInterfaceScan(
                    interface=interface,
                    bss_entries=(),
                    requested_fresh_scan=True,
                    scan_wait_seconds=0.0,
                    wait_strategy="test",
                ),
            ),
        )


def _project(tmp_path):
    project = tmp_path / "project"
    (project / "backend").mkdir(parents=True)
    (project / "backend" / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    snapshot = compute_implementation_snapshot(project)
    path = project / "reports" / "implementation" / "implementation_snapshot_step52.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    return project


def test_collection_readiness_blocks_non_windows(tmp_path):
    project = _project(tmp_path)
    result = inspect_collection_readiness(project, platform_name="linux")
    assert result["ready"] is False
    assert "windows_host_required" in result["blockers"]


def test_collection_readiness_can_pass_windows_with_probe_and_frozen_implementation(tmp_path):
    project = _project(tmp_path)
    result = inspect_collection_readiness(
        project,
        platform_name="win32",
        probe_native_wifi=True,
        scanner=ReadyScanner(),
    )
    assert result["status"] == "READY_FOR_NORMAL_COLLECTION"
    assert result["scanner_probe"]["executed"] is True
    assert result["scanner_probe"]["interface_count"] == 1
    assert result["scanner_probe"]["identifiers_recorded"] is False


def test_collection_readiness_blocks_existing_scientific_freeze(tmp_path):
    project = _project(tmp_path)
    frozen = project / "data" / "processed" / "desktop_candidate_v1"
    frozen.mkdir(parents=True)
    (frozen / "scientific_freeze.json").write_text("{}", encoding="utf-8")

    result = inspect_collection_readiness(
        project,
        platform_name="win32",
        probe_native_wifi=True,
        scanner=ReadyScanner(),
    )
    assert result["ready"] is False
    assert "desktop_candidate_v1_already_frozen" in result["blockers"]
