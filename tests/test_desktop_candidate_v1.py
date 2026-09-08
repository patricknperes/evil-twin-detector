from desktop.features.desktop_candidate_v1 import (
    DESKTOP_CANDIDATE_V1_FEATURES,
    build_desktop_reference,
    compute_desktop_candidate_v1,
)
from desktop.windows.native_wifi_contract import NativeWifiBssObservation


def ie(element_id, payload):
    return bytes([element_id, len(payload)]) + payload


def rsn_payload(akm_type):
    return (
        b"\x01\x00"
        + b"\x00\x0f\xac\x04"
        + b"\x01\x00"
        + b"\x00\x0f\xac\x04"
        + b"\x01\x00"
        + bytes([0x00, 0x0F, 0xAC, akm_type])
    )


def obs(ssid, bssid, security_blob=b"", capability=0):
    return NativeWifiBssObservation(
        ssid=ssid,
        bssid=bssid,
        rssi_dbm=-55,
        link_quality=90,
        beacon_period_tu=100,
        tsf_us=123456,
        host_timestamp_100ns=10,
        capability_info=capability,
        center_frequency_khz=2437000,
        ie_blob=security_blob,
    )


def test_reference_and_unchanged_observation():
    normal = obs(
        b"Rede",
        "00:11:22:33:44:55",
        ie(48, rsn_payload(2)),
        capability=1 << 4,
    )
    reference = build_desktop_reference([normal])
    result = compute_desktop_candidate_v1(normal, reference)

    assert result.context_available is True
    assert list(result.features) == DESKTOP_CANDIDATE_V1_FEATURES
    assert result.features == {
        "ssid_bssid_count": 1.0,
        "bssid_changed": 0.0,
        "security_changed": 0.0,
        "security_strength_delta": 0.0,
    }


def test_new_bssid_and_security_downgrade():
    normal = obs(
        b"Rede",
        "00:11:22:33:44:55",
        ie(48, rsn_payload(2)),
        capability=1 << 4,
    )
    reference = build_desktop_reference([normal])

    suspicious = obs(
        b"Rede",
        "02:AA:BB:CC:DD:EE",
        b"",
        capability=0,
    )
    result = compute_desktop_candidate_v1(suspicious, reference)

    assert result.features["bssid_changed"] == 1.0
    assert result.features["security_changed"] == 1.0
    assert result.features["security_strength_delta"] == -3.0


def test_zero_length_ssid_is_metadata_not_model_feature():
    normal = obs(
        b"Rede",
        "00:11:22:33:44:55",
        ie(48, rsn_payload(2)),
        capability=1 << 4,
    )
    reference = build_desktop_reference([normal])

    hidden_like = obs(
        b"",
        "00:11:22:33:44:55",
        ie(48, rsn_payload(2)),
        capability=1 << 4,
    )
    result = compute_desktop_candidate_v1(hidden_like, reference)

    assert result.context_available is True
    assert result.context_resolution == "bssid_fallback"
    assert result.metadata["ssid_not_broadcast"] is True
    assert "is_hidden" not in result.features


def test_unknown_ssid_has_no_context_instead_of_forced_anomaly():
    normal = obs(b"Known", "00:11:22:33:44:55")
    reference = build_desktop_reference([normal])

    unknown = obs(b"Other", "00:AA:BB:CC:DD:EE")
    result = compute_desktop_candidate_v1(unknown, reference)

    assert result.context_available is False
    assert result.features == {}
