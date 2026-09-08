import json

from desktop.windows.native_wifi_contract import NativeWifiBssObservation
from desktop.windows.normal_collection import collect_normal_session
from desktop.windows.scan_serialization import hash_ssid_identifier
from desktop.windows.wlanapi_ctypes import (
    NativeWifiBssNativeMetadata,
    NativeWifiBssResult,
    NativeWifiInterface,
    NativeWifiInterfaceScan,
    NativeWifiScanBatch,
)


class FakeScanner:
    def __init__(self):
        self.index = 0

    def scan_all(self, **kwargs):
        self.index += 1
        tsf = self.index * 1000

        observation = NativeWifiBssObservation(
            ssid=b"Rede",
            bssid="00:11:22:33:44:55",
            rssi_dbm=-48,
            link_quality=90,
            beacon_period_tu=100,
            tsf_us=tsf,
            host_timestamp_100ns=tsf * 10,
            capability_info=0,
            center_frequency_khz=2437000,
            ie_blob=bytes([3, 1, 6]),
        )

        native = NativeWifiBssNativeMetadata(
            phy_id=1,
            bss_type_code=1,
            bss_type="infrastructure",
            phy_type_code=7,
            phy_type="ht",
            in_reg_domain=True,
            supported_rates_mbps=(6.0,),
        )

        interface = NativeWifiInterface(
            guid="GUID-1",
            description="Fake Wi-Fi",
            state_code=1,
            state="connected",
            _guid_struct=None,
        )

        return NativeWifiScanBatch(
            negotiated_api_version=2,
            interface_scans=(
                NativeWifiInterfaceScan(
                    interface=interface,
                    bss_entries=(
                        NativeWifiBssResult(
                            observation=observation,
                            native=native,
                        ),
                    ),
                    requested_fresh_scan=True,
                    scan_wait_seconds=0.0,
                    wait_strategy="fake",
                ),
            ),
        )


def test_collection_creates_raw_session(tmp_path):
    result = collect_normal_session(
        environment="lab-a",
        output_root=tmp_path,
        scanner=FakeScanner(),
        scans=3,
        interval_seconds=0,
        scan_wait_seconds=0,
        session_id="session-test",
        sleep_fn=lambda _: None,
    )

    folder = tmp_path / "session-test"

    manifest = json.loads(
        (folder / "manifest.json").read_text(encoding="utf-8")
    )

    assert manifest["label"] == 0
    assert manifest["attack_present"] is False
    assert manifest["privacy"]["identifiers_in_clear_text"] is False
    assert result["runtime_validation"][
        "runtime_ready_for_own_normal_collection"
    ] is True

    first = json.loads(
        (folder / "scans.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )["interfaces"][0]["bss_entries"][0]

    assert first["ssid_hash"]
    assert first["bssid_hash"]
    assert "ssid" not in first
    assert "bssid" not in first


def test_collection_refuses_overwrite(tmp_path):
    scanner = FakeScanner()

    collect_normal_session(
        environment="lab-a",
        output_root=tmp_path,
        scanner=scanner,
        scans=1,
        interval_seconds=0,
        scan_wait_seconds=0,
        session_id="same",
        sleep_fn=lambda _: None,
    )

    try:
        collect_normal_session(
            environment="lab-a",
            output_root=tmp_path,
            scanner=scanner,
            scans=1,
            interval_seconds=0,
            scan_wait_seconds=0,
            session_id="same",
            sleep_fn=lambda _: None,
        )
    except FileExistsError:
        pass
    else:
        raise AssertionError("Expected FileExistsError")



def test_ssid_hash_contract_matches_raw_windows_bytes_and_runtime_text():
    raw = b"Cafe-\xff-WiFi"
    runtime_text = raw.decode(
        "utf-8",
        errors="replace",
    )

    assert (
        hash_ssid_identifier(
            raw
        )
        == hash_ssid_identifier(
            runtime_text
        )
    )
