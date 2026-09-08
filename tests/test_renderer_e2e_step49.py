from __future__ import annotations

import json

from backend.runtime_paths import (
    resource_root,
)


def test_playwright_electron_e2e_source_contract_is_declared():
    root = resource_root()

    package = json.loads(
        (
            root
            / "frontend"
            / "package.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert (
        "@playwright/test"
        in package[
            "devDependencies"
        ]
    )

    assert (
        "playwright"
        in package[
            "devDependencies"
        ]
    )

    assert (
        package[
            "scripts"
        ][
            "e2e"
        ]
        == "playwright test -c playwright.config.ts"
    )

    assert (
        root
        / "frontend"
        / "playwright.config.ts"
    ).exists()

    assert (
        root
        / "frontend"
        / "e2e"
        / "desktop.e2e.ts"
    ).exists()


def test_e2e_ipc_is_strictly_environment_gated():
    root = resource_root()

    main = (
        root
        / "frontend"
        / "electron"
        / "main.cjs"
    ).read_text(
        encoding="utf-8"
    )

    preload = (
        root
        / "frontend"
        / "electron"
        / "preload.cjs"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        'EVIL_TWIN_E2E'
        in main
    )

    assert (
        '"desktop:e2e-run-auto-scan"'
        in main
    )

    assert (
        "if (\n  e2eMode\n)"
        in main
    )

    assert (
        "e2eRunAutoScan"
        in preload
    )

    assert (
        "e2eMode"
        in preload
    )


def test_e2e_mode_suppresses_real_os_notifications():
    root = resource_root()

    main = (
        root
        / "frontend"
        / "electron"
        / "main.cjs"
    ).read_text(
        encoding="utf-8"
    )

    marker = (
        "function showHighSuspicionNotification"
    )

    section = main[
        main.index(
            marker
        ):
        main.index(
            "const autoScanScheduler"
        )
    ]

    assert (
        "if (\n    e2eMode\n  )"
        in section
    )

    assert (
        section.index(
            "e2eMode"
        )
        < section.index(
            "Notification.isSupported"
        )
    )


def test_final_e2e_source_uses_fake_backend_not_native_wifi():
    root = resource_root()

    e2e = (
        root
        / "frontend"
        / "e2e"
        / "desktop.e2e.ts"
    ).read_text(
        encoding="utf-8"
    )

    fake = (
        root
        / "frontend"
        / "e2e"
        / "support"
        / "fake-backend.ts"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "FakeDesktopBackend"
        in e2e
    )

    assert (
        "EVIL_TWIN_E2E_FORCE_SCHEDULER"
        in e2e
    )

    assert (
        "collect_windows"
        not in e2e
    )

    assert (
        "wlanapi"
        not in fake.lower()
    )

    assert (
        "não é resultado científico"
        in fake
    )


def test_e2e_diagnostics_scenario_checks_forbidden_identifier_keys():
    root = resource_root()

    e2e = (
        root
        / "frontend"
        / "e2e"
        / "desktop.e2e.ts"
    ).read_text(
        encoding="utf-8"
    )

    for key in (
        '"ssid"',
        '"bssid"',
        '"ssid_hash"',
        '"bssid_hash"',
        '"interface_guid"',
        '"raw_ie_hex"',
    ):
        assert (
            key
            in e2e
        )
