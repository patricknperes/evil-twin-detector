from __future__ import annotations

import time
from dataclasses import dataclass

from .wlanapi_ctypes import (
    NativeWifiApi,
    NativeWifiInterface,
    NativeWifiInterfaceScan,
    NativeWifiScanBatch,
    NativeWifiSession,
)


DEFAULT_SCAN_WAIT_SECONDS = 4.2


class NativeWifiScanner:
    """High-level scanner that converts wlanapi.dll results into project contracts.

    WlanScan is asynchronous. Microsoft recommends waiting for the ACM scan
    completion notification or timing out after four seconds. Step 16 uses a
    bounded fixed wait to keep the first adapter small and easy to diagnose.
    Notification-driven waiting is intentionally a later hardening step.
    """

    def __init__(
        self,
        api: NativeWifiApi | None = None,
        *,
        sleep_fn=time.sleep,
    ) -> None:
        self.api = api or NativeWifiApi()
        self._sleep = sleep_fn

    def enumerate_interfaces(self) -> tuple[NativeWifiInterface, ...]:
        with NativeWifiSession(self.api) as session:
            return self.api.enum_interfaces(session.require_handle())

    def scan_all(
        self,
        *,
        request_fresh_scan: bool = True,
        scan_wait_seconds: float = DEFAULT_SCAN_WAIT_SECONDS,
        interface_guid: str | None = None,
    ) -> NativeWifiScanBatch:
        if scan_wait_seconds < 0:
            raise ValueError("scan_wait_seconds must be >= 0")

        with NativeWifiSession(self.api) as session:
            handle = session.require_handle()
            interfaces = self.api.enum_interfaces(handle)

            if interface_guid is not None:
                wanted = interface_guid.strip().upper()
                interfaces = tuple(
                    interface
                    for interface in interfaces
                    if interface.guid.upper() == wanted
                )

            scans: list[NativeWifiInterfaceScan] = []

            for interface in interfaces:
                if request_fresh_scan:
                    self.api.request_scan(handle, interface)
                    if scan_wait_seconds:
                        self._sleep(scan_wait_seconds)

                entries = self.api.get_bss_list(handle, interface)
                scans.append(
                    NativeWifiInterfaceScan(
                        interface=interface,
                        bss_entries=entries,
                        requested_fresh_scan=request_fresh_scan,
                        scan_wait_seconds=float(scan_wait_seconds) if request_fresh_scan else 0.0,
                        wait_strategy=(
                            "fixed_timeout_after_WlanScan"
                            if request_fresh_scan
                            else "cached_list_no_scan_request"
                        ),
                    )
                )

            return NativeWifiScanBatch(
                negotiated_api_version=int(session.negotiated_api_version or 0),
                interface_scans=tuple(scans),
            )
