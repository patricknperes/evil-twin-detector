from __future__ import annotations

from threading import RLock

from .schemas import ScanResponse


class RuntimeStore:
    """Thread-safe latest-scan state. SQLite arrives in the next step."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._latest_scan: ScanResponse | None = None

    def set_latest_scan(
        self,
        scan: ScanResponse,
    ) -> None:
        with self._lock:
            self._latest_scan = scan

    def get_latest_scan(
        self,
    ) -> ScanResponse | None:
        with self._lock:
            return self._latest_scan
