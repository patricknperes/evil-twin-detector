import sys

import pytest

from desktop.windows.wlanapi_ctypes import (
    NativeWifiApi,
    UnsupportedPlatformError,
)
from desktop.windows.diagnostic import run_diagnostic


def test_native_api_is_guarded_off_windows():
    if sys.platform == "win32":
        pytest.skip("This assertion is for non-Windows CI.")
    with pytest.raises(UnsupportedPlatformError):
        NativeWifiApi()


def test_diagnostic_returns_structured_unsupported_platform_off_windows():
    if sys.platform == "win32":
        pytest.skip("This assertion is for non-Windows CI.")
    code, payload = run_diagnostic()
    assert code == 2
    assert payload["status"] == "unsupported_platform"
