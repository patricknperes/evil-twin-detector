from __future__ import annotations
import hashlib
import re
import numpy as np
import pandas as pd

_MAC_RE = re.compile(
    r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$"
)

def clean_bssid(value):
    if pd.isna(value):
        return None
    text = str(value).strip().upper()
    return text if _MAC_RE.match(text) else None

def hash_bssid(value):
    value = clean_bssid(value)
    if value is None:
        return None
    return hashlib.sha256(
        ("bssid|" + value).encode("utf-8")
    ).hexdigest()

def bssid_local_admin_flag(value):
    """
    IEEE 802 U/L bit (bit 1 of first octet).
    1 = locally administered.
    This is not an attack label.
    """
    bssid = clean_bssid(value)
    if bssid is None:
        return np.nan
    first_octet = int(bssid.split(":")[0], 16)
    return float(bool(first_octet & 0x02))

def bssid_multicast_flag(value):
    """IEEE 802 I/G bit (bit 0 of first octet)."""
    bssid = clean_bssid(value)
    if bssid is None:
        return np.nan
    first_octet = int(bssid.split(":")[0], 16)
    return float(bool(first_octet & 0x01))

def transform_local_admin(df):
    return pd.DataFrame({
        "bssid_hash": df["bssid"].map(hash_bssid),
        "bssid_local_admin_flag": df["bssid"].map(
            bssid_local_admin_flag
        ),
        "bssid_multicast_flag": df["bssid"].map(
            bssid_multicast_flag
        ),
    })
