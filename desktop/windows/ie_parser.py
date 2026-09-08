from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


IE_SSID = 0
IE_DS_PARAMETER_SET = 3
IE_RSN = 48
IE_VENDOR_SPECIFIC = 221

RSN_OUI = b"\x00\x0f\xac"
WPA_VENDOR_PREFIX = b"\x00\x50\xf2\x01"

# IEEE RSN AKM suite types relevant to a conservative WPA3 label.
AKM_SAE = 8
AKM_FT_SAE = 9

PRIVACY_CAPABILITY_BIT = 1 << 4

SECURITY_STRENGTH = {
    "OPEN": 0,
    "LEGACY_PRIVACY": 1,
    "WPA": 2,
    "WPA2_OR_NEWER": 3,
    "WPA3_SAE": 4,
}


@dataclass(frozen=True)
class InformationElement:
    element_id: int
    data: bytes


@dataclass(frozen=True)
class ParsedInformationElements:
    elements: tuple[InformationElement, ...]
    truncated: bool

    def by_id(self, element_id: int) -> tuple[bytes, ...]:
        return tuple(
            element.data
            for element in self.elements
            if element.element_id == element_id
        )


@dataclass(frozen=True)
class SecurityObservation:
    security_type: str
    strength: int
    source: str
    rsn_akm_types: tuple[int, ...] = ()


def parse_information_elements(blob: bytes) -> ParsedInformationElements:
    """Parse the generic 802.11 IE TLV format with strict length bounds.

    Microsoft documents ulIeOffset/ulIeSize as an untrusted blob. A malformed
    element never causes reads beyond the provided bytes; parsing stops and the
    result is marked truncated.
    """
    elements: list[InformationElement] = []
    offset = 0
    truncated = False

    while offset < len(blob):
        if offset + 2 > len(blob):
            truncated = True
            break

        element_id = blob[offset]
        length = blob[offset + 1]
        start = offset + 2
        end = start + length

        if end > len(blob):
            truncated = True
            break

        elements.append(
            InformationElement(
                element_id=element_id,
                data=bytes(blob[start:end]),
            )
        )
        offset = end

    return ParsedInformationElements(
        elements=tuple(elements),
        truncated=truncated,
    )


def _read_u16_le(data: bytes, offset: int) -> tuple[int | None, int]:
    if offset + 2 > len(data):
        return None, offset
    return int.from_bytes(data[offset : offset + 2], "little"), offset + 2


def parse_rsn_akm_types(rsn_data: bytes) -> tuple[int, ...]:
    """Return RSN AKM suite type bytes when the RSN structure is complete.

    This intentionally does not attempt a complete RSN policy engine. It only
    extracts the AKM list needed to distinguish SAE/FT-SAE from a generic RSN
    network for the desktop feature contract.
    """
    if len(rsn_data) < 8:
        return ()

    offset = 0
    version, offset = _read_u16_le(rsn_data, offset)
    if version is None:
        return ()

    # Group Data Cipher Suite
    if offset + 4 > len(rsn_data):
        return ()
    offset += 4

    pairwise_count, offset = _read_u16_le(rsn_data, offset)
    if pairwise_count is None:
        return ()

    pairwise_bytes = 4 * pairwise_count
    if offset + pairwise_bytes > len(rsn_data):
        return ()
    offset += pairwise_bytes

    akm_count, offset = _read_u16_le(rsn_data, offset)
    if akm_count is None:
        return ()

    akm_types: list[int] = []
    for _ in range(akm_count):
        if offset + 4 > len(rsn_data):
            return ()
        suite = rsn_data[offset : offset + 4]
        offset += 4
        if suite[:3] == RSN_OUI:
            akm_types.append(suite[3])

    return tuple(akm_types)


def _has_wpa_vendor_ie(elements: Iterable[InformationElement]) -> bool:
    return any(
        element.element_id == IE_VENDOR_SPECIFIC
        and element.data.startswith(WPA_VENDOR_PREFIX)
        for element in elements
    )


def infer_security(capability_info: int, ie_blob: bytes) -> SecurityObservation:
    parsed = parse_information_elements(ie_blob)
    rsn_payloads = parsed.by_id(IE_RSN)

    if rsn_payloads:
        akm_types: list[int] = []
        for payload in rsn_payloads:
            akm_types.extend(parse_rsn_akm_types(payload))

        unique_akm = tuple(sorted(set(akm_types)))
        if AKM_SAE in unique_akm or AKM_FT_SAE in unique_akm:
            security_type = "WPA3_SAE"
        else:
            security_type = "WPA2_OR_NEWER"

        return SecurityObservation(
            security_type=security_type,
            strength=SECURITY_STRENGTH[security_type],
            source="rsn_ie",
            rsn_akm_types=unique_akm,
        )

    parsed_elements = parsed.elements
    if _has_wpa_vendor_ie(parsed_elements):
        return SecurityObservation(
            security_type="WPA",
            strength=SECURITY_STRENGTH["WPA"],
            source="wpa_vendor_ie",
        )

    if capability_info & PRIVACY_CAPABILITY_BIT:
        return SecurityObservation(
            security_type="LEGACY_PRIVACY",
            strength=SECURITY_STRENGTH["LEGACY_PRIVACY"],
            source="capability_privacy_bit",
        )

    return SecurityObservation(
        security_type="OPEN",
        strength=SECURITY_STRENGTH["OPEN"],
        source="capability_privacy_bit",
    )


def extract_ds_parameter_channel(ie_blob: bytes) -> int | None:
    """Return DS Parameter Set channel only when a 1-byte IE is present.

    This is intentionally a partial helper. It must not be treated as a
    universal advertised-channel implementation for every PHY/band.
    """
    parsed = parse_information_elements(ie_blob)
    for payload in parsed.by_id(IE_DS_PARAMETER_SET):
        if len(payload) == 1 and payload[0] > 0:
            return int(payload[0])
    return None
