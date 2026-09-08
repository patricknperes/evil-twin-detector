from __future__ import annotations

from threading import Event, Thread

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.model_status import ModelArtifactStatusService
from backend.runtime_store import RuntimeStore
from backend.scanner_service import ScannerService
from desktop.windows.wlanapi_ctypes import NativeWifiScanBatch


class BlockingScanner:
    def __init__(self) -> None:
        self.entered = Event()
        self.release = Event()

    def scan_all(self, **kwargs) -> NativeWifiScanBatch:
        self.entered.set()

        if not self.release.wait(timeout=5):
            raise RuntimeError("test scanner release timeout")

        return NativeWifiScanBatch(
            negotiated_api_version=2,
            interface_scans=(),
        )


def test_second_scan_is_rejected_while_first_is_running(tmp_path):
    native = BlockingScanner()

    app = create_app(
        scanner_service=ScannerService(scanner=native),
        runtime_store=RuntimeStore(),
        model_status_service=ModelArtifactStatusService(
            project_root=tmp_path
        ),
    )

    first_client = TestClient(app)
    second_client = TestClient(app)
    first_result = {}

    def run_first():
        first_result["response"] = first_client.post(
            "/scan",
            json={
                "request_fresh_scan": False,
                "scan_wait_seconds": 0,
            },
        )

    thread = Thread(target=run_first)
    thread.start()

    assert native.entered.wait(timeout=2)

    second = second_client.post(
        "/scan",
        json={
            "request_fresh_scan": False,
            "scan_wait_seconds": 0,
        },
    )

    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "scan_in_progress"

    native.release.set()
    thread.join(timeout=5)

    assert thread.is_alive() is False
    assert first_result["response"].status_code == 200
