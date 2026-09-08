from __future__ import annotations

import ctypes
import json
from pathlib import Path

from desktop.windows.wlanapi_ctypes import (
    DOT11_SSID,
    WLAN_RATE_SET,
    WLAN_INTERFACE_INFO,
    WLAN_BSS_ENTRY,
    WLAN_BSS_LIST,
)


def validate_step16(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root)
    config = json.loads(
        (root / "config" / "windows_native_wifi_scanner.json").read_text(
            encoding="utf-8"
        )
    )

    assert config["phase"] == 4
    assert config["step"] == 16
    assert config["status"] == "ctypes_scanner_ready_windows_runtime_validation_pending"

    # Fixed-width structure layout is intentionally testable off Windows.
    assert ctypes.sizeof(DOT11_SSID) == 36
    assert ctypes.sizeof(WLAN_RATE_SET) == 256
    assert ctypes.sizeof(WLAN_BSS_ENTRY) == 360
    assert ctypes.sizeof(WLAN_INTERFACE_INFO) == 532
    assert WLAN_BSS_LIST.wlanBssEntries.offset == 8

    return config


if __name__ == "__main__":
    validate_step16()
    print("Fase 4 / Passo 16 validado.")
