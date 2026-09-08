from __future__ import annotations

import pytest

from backend.scanner_service import ScannerService
from backend.schemas import ScanRequest
from desktop.windows.wlanapi_ctypes import (
    LocationAccessDeniedError,
    NativeWifiApiError,
    NativeWifiScanBatch,
    UnsupportedPlatformError,
)

class SuccessfulScanner:
    def scan_all(self, **kwargs) -> NativeWifiScanBatch:
        return NativeWifiScanBatch(negotiated_api_version=2, interface_scans=())

class ErrorScanner:
    def __init__(self, error): self.error=error
    def scan_all(self, **kwargs): raise self.error

def request() -> ScanRequest:
    return ScanRequest(request_fresh_scan=False, scan_wait_seconds=0)

def test_scanner_runtime_is_not_initialized_before_first_scan():
    service=ScannerService(scanner=SuccessfulScanner())
    assert service.runtime_status == "not_initialized"

def test_successful_scan_marks_scanner_ready():
    service=ScannerService(scanner=SuccessfulScanner()); service.scan(request())
    assert service.runtime_status == "ready"

def test_location_denied_is_preserved_as_runtime_state():
    service=ScannerService(scanner=ErrorScanner(LocationAccessDeniedError("WlanGetNetworkBssList",5,"Access denied")))
    with pytest.raises(LocationAccessDeniedError): service.scan(request())
    assert service.runtime_status == "location_access_denied"

def test_unsupported_platform_is_preserved_as_runtime_state():
    service=ScannerService(scanner=ErrorScanner(UnsupportedPlatformError("Windows Native Wi-Fi is unavailable.")))
    with pytest.raises(UnsupportedPlatformError): service.scan(request())
    assert service.runtime_status == "unsupported_platform"

def test_native_wifi_error_marks_scanner_error():
    service=ScannerService(scanner=ErrorScanner(NativeWifiApiError("WlanScan",123,"Native error")))
    with pytest.raises(NativeWifiApiError): service.scan(request())
    assert service.runtime_status == "error"

def test_scanner_recovers_to_ready_after_previous_error():
    class RecoveringScanner:
        def __init__(self): self.calls=0
        def scan_all(self, **kwargs):
            self.calls += 1
            if self.calls == 1: raise LocationAccessDeniedError("WlanGetNetworkBssList",5,"Access denied")
            return NativeWifiScanBatch(negotiated_api_version=2, interface_scans=())
    service=ScannerService(scanner=RecoveringScanner())
    with pytest.raises(LocationAccessDeniedError): service.scan(request())
    assert service.runtime_status == "location_access_denied"
    service.scan(request())
    assert service.runtime_status == "ready"
