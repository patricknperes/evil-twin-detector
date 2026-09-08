from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import uuid4

from desktop.windows.ie_parser import (
    extract_ds_parameter_channel,
)
from desktop.windows.scanner import (
    NativeWifiScanner,
)
from desktop.windows.wlanapi_ctypes import (
    LocationAccessDeniedError,
    NativeWifiApiError,
    UnsupportedPlatformError,
)

from .schemas import (
    InterfaceSummary,
    NetworkObservationResponse,
    ScanRequest,
    ScanResponse,
)


def _network_id(
    *,
    interface_guid: str,
    bssid: str,
) -> str:
    return hashlib.sha256(
        (
            f"{interface_guid}|{bssid}"
        ).encode("utf-8")
    ).hexdigest()


def _ssid_text(value: bytes) -> str:
    return value.decode(
        "utf-8",
        errors="replace",
    )


class ScannerService:
    """
    Product adapter around NativeWifiScanner.

    Important: the native scanner is initialized lazily on first scan.
    Importing the FastAPI application therefore remains safe on Linux/macOS
    CI and during build tooling.
    """

    def __init__(
        self,
        scanner=None,
    ) -> None:
        self._scanner = scanner
        self._runtime_status = "not_initialized"

    @property
    def initialized(
        self,
    ) -> bool:
        return self._scanner is not None

    @property
    def runtime_status(
        self,
    ) -> str:
        return self._runtime_status

    def _require_scanner(
        self,
    ):
        if self._scanner is None:
            self._scanner = (
                NativeWifiScanner()
            )

        return self._scanner

    def scan(
        self,
        request: ScanRequest,
    ) -> ScanResponse:
        try:
            scanner = self._require_scanner()

            observed_at = datetime.now(
                timezone.utc
            )

            batch = scanner.scan_all(
                request_fresh_scan=(
                    request.request_fresh_scan
                ),
                scan_wait_seconds=(
                    request.scan_wait_seconds
                ),
                interface_guid=(
                    request.interface_guid
                ),
            )
        except LocationAccessDeniedError:
            self._runtime_status = "location_access_denied"
            raise
        except UnsupportedPlatformError:
            self._runtime_status = "unsupported_platform"
            raise
        except NativeWifiApiError:
            self._runtime_status = "error"
            raise
        except Exception:
            self._runtime_status = "error"
            raise

        self._runtime_status = "ready"

        interfaces = []
        networks = []

        for interface_scan in batch.interface_scans:
            interface = interface_scan.interface

            interfaces.append(
                InterfaceSummary(
                    guid=interface.guid,
                    description=interface.description,
                    state_code=interface.state_code,
                    state=interface.state,
                    requested_fresh_scan=(
                        interface_scan.requested_fresh_scan
                    ),
                    scan_wait_seconds=(
                        interface_scan.scan_wait_seconds
                    ),
                    wait_strategy=(
                        interface_scan.wait_strategy
                    ),
                    bss_count=len(
                        interface_scan.bss_entries
                    ),
                )
            )

            for result in interface_scan.bss_entries:
                observation = result.observation
                security = observation.security

                networks.append(
                    NetworkObservationResponse(
                        network_id=_network_id(
                            interface_guid=interface.guid,
                            bssid=observation.bssid,
                        ),
                        interface_guid=interface.guid,
                        ssid=_ssid_text(
                            observation.ssid
                        ),
                        bssid=observation.bssid,
                        ssid_not_broadcast=(
                            observation.ssid_not_broadcast
                        ),
                        rssi_dbm=observation.rssi_dbm,
                        link_quality=observation.link_quality,
                        beacon_interval_ms=(
                            observation.beacon_interval_ms
                        ),
                        tsf_us=observation.tsf_us,
                        host_timestamp_100ns=(
                            observation.host_timestamp_100ns
                        ),
                        center_frequency_khz=(
                            observation.center_frequency_khz
                        ),
                        ds_parameter_channel=(
                            extract_ds_parameter_channel(
                                observation.ie_blob
                            )
                        ),
                        security_type=(
                            security.security_type
                        ),
                        security_strength=(
                            security.strength
                        ),
                        security_source=(
                            security.source
                        ),
                        phy_type=result.native.phy_type,
                        bss_type=result.native.bss_type,
                        supported_rates_mbps=list(
                            result.native.supported_rates_mbps
                        ),
                    )
                )

        networks.sort(
            key=lambda item: (
                -item.rssi_dbm,
                item.ssid.lower(),
                item.bssid,
            )
        )

        return ScanResponse(
            scan_id=str(uuid4()),
            observed_at_utc=observed_at,
            negotiated_api_version=(
                batch.negotiated_api_version
            ),
            interface_count=len(
                batch.interface_scans
            ),
            total_networks=len(networks),
            interfaces=interfaces,
            networks=networks,
        )
