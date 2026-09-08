from desktop.windows.ie_parser import (
    SECURITY_STRENGTH,
    extract_ds_parameter_channel,
    infer_security,
    parse_information_elements,
)


def ie(element_id, payload):
    return bytes([element_id, len(payload)]) + payload


def rsn_payload(akm_type):
    # version=1, group cipher=CCMP, pairwise count=1 CCMP,
    # AKM count=1, selected RSN AKM type.
    return (
        b"\x01\x00"
        + b"\x00\x0f\xac\x04"
        + b"\x01\x00"
        + b"\x00\x0f\xac\x04"
        + b"\x01\x00"
        + bytes([0x00, 0x0F, 0xAC, akm_type])
    )


def test_ie_parser_stops_on_truncated_element():
    parsed = parse_information_elements(
        b"\x00\x03abc" + b"\x30\x08\x01\x00"
    )
    assert parsed.truncated is True
    assert len(parsed.elements) == 1
    assert parsed.elements[0].data == b"abc"


def test_security_open_and_legacy_privacy():
    open_security = infer_security(0, b"")
    assert open_security.security_type == "OPEN"
    assert open_security.strength == SECURITY_STRENGTH["OPEN"]

    legacy = infer_security(1 << 4, b"")
    assert legacy.security_type == "LEGACY_PRIVACY"


def test_security_wpa_vendor_ie():
    blob = ie(221, b"\x00\x50\xf2\x01\x01\x00")
    result = infer_security(1 << 4, blob)
    assert result.security_type == "WPA"
    assert result.source == "wpa_vendor_ie"


def test_security_rsn_psk_is_wpa2_or_newer():
    blob = ie(48, rsn_payload(2))
    result = infer_security(1 << 4, blob)
    assert result.security_type == "WPA2_OR_NEWER"
    assert result.rsn_akm_types == (2,)


def test_security_rsn_sae_is_wpa3():
    blob = ie(48, rsn_payload(8))
    result = infer_security(1 << 4, blob)
    assert result.security_type == "WPA3_SAE"
    assert result.rsn_akm_types == (8,)


def test_ds_parameter_is_partial_helper():
    blob = ie(3, b"\x06")
    assert extract_ds_parameter_channel(blob) == 6
    assert extract_ds_parameter_channel(ie(3, b"\x00")) is None
