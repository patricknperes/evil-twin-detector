from __future__ import annotations

from backend.runtime_paths import (
    resource_root,
)
from desktop.release_preflight import (
    POST_BUILD_STAGE_IDS,
    RELEASE_INPUT_STAGE_IDS,
    evaluate_release_preflight,
    inspect_release_preflight,
)


def _readiness(
    *,
    override=None,
    include_post_build=False,
):
    override = (
        override
        or {}
    )

    stage_ids = list(
        RELEASE_INPUT_STAGE_IDS
    )

    if include_post_build:
        stage_ids.extend(
            POST_BUILD_STAGE_IDS
        )

    return {
        "overall_status":
            "BLOCKED",
        "stages": [
            {
                "id":
                    stage_id,
                "status":
                    override.get(
                        stage_id,
                        "READY",
                    ),
            }
            for stage_id
            in stage_ids
        ],
    }


def _backend_packaging():
    return {
        "static_ready":
            True,
        "scientific_ready":
            True,
    }


def _desktop_packaging(
    *,
    production=True,
):
    return {
        "structural_ready":
            True,
        "production_ready":
            production,
    }


def test_release_inputs_ready_only_when_all_pre_release_gates_are_ready():
    result = (
        evaluate_release_preflight(
            readiness=(
                _readiness()
            ),
            backend_packaging=(
                _backend_packaging()
            ),
            desktop_packaging=(
                _desktop_packaging()
            ),
            target="inputs",
        )
    )

    assert (
        result[
            "status"
        ]
        == "READY_FOR_RELEASE_BUILD"
    )

    assert (
        result[
            "ready"
        ]
        is True
    )


def test_release_preflight_blocks_pending_renderer_e2e():
    result = (
        evaluate_release_preflight(
            readiness=(
                _readiness(
                    override={
                        "renderer_electron_e2e":
                            "NOT_EXECUTED",
                    }
                )
            ),
            backend_packaging=(
                _backend_packaging()
            ),
            desktop_packaging=(
                _desktop_packaging()
            ),
            target="inputs",
        )
    )

    assert (
        result[
            "ready"
        ]
        is False
    )

    assert (
        "readiness_stage_not_ready:"
        "renderer_electron_e2e:"
        "NOT_EXECUTED"
        in result[
            "blockers"
        ]
    )


def test_installer_preflight_requires_frontend_dist_and_backend_exe_contract():
    result = (
        evaluate_release_preflight(
            readiness=(
                _readiness()
            ),
            backend_packaging=(
                _backend_packaging()
            ),
            desktop_packaging=(
                _desktop_packaging(
                    production=False
                )
            ),
            target="installer",
        )
    )

    assert (
        result[
            "ready"
        ]
        is False
    )

    assert (
        "desktop_packaging_products_not_ready"
        in result[
            "blockers"
        ]
    )


def test_post_build_verification_requires_current_installer_and_packaging_stages():
    ready = (
        evaluate_release_preflight(
            readiness=(
                _readiness(
                    include_post_build=True
                )
            ),
            backend_packaging=(
                _backend_packaging()
            ),
            desktop_packaging=(
                _desktop_packaging()
            ),
            target="verify",
            installer_count=1,
        )
    )

    assert (
        ready[
            "status"
        ]
        == "READY_FOR_DISTRIBUTION"
    )

    missing_installer = (
        evaluate_release_preflight(
            readiness=(
                _readiness(
                    include_post_build=True
                )
            ),
            backend_packaging=(
                _backend_packaging()
            ),
            desktop_packaging=(
                _desktop_packaging()
            ),
            target="verify",
            installer_count=0,
        )
    )

    assert (
        "expected_exactly_one_current_installer"
        in missing_installer[
            "blockers"
        ]
    )


def test_current_project_release_preflight_is_truthfully_blocked():
    report = (
        inspect_release_preflight(
            resource_root(),
            target="inputs",
            platform_name="linux",
        )
    )

    assert (
        report[
            "status"
        ]
        == "BLOCKED_RELEASE_PREFLIGHT"
    )

    assert (
        report[
            "ready"
        ]
        is False
    )

    assert any(
        blocker.startswith(
            "readiness_stage_not_ready:"
            "windows_execution_host:"
        )
        for blocker
        in report[
            "blockers"
        ]
    )


def test_windows_powershell_scripts_do_not_use_ps7_iswindows_automatic_variable():
    root = resource_root()

    powershell_files = list(
        (
            root
            / "scripts"
        ).glob(
            "*.ps1"
        )
    )

    offenders = []

    for path in powershell_files:
        text = path.read_text(
            encoding="utf-8"
        )

        if "$IsWindows" in text:
            offenders.append(
                path.name
            )

    assert (
        offenders
        == []
    )


def test_windows_build_scripts_use_shared_cross_version_host_check():
    root = resource_root()

    for filename in (
        "build_backend_windows.ps1",
        "build_desktop_installer_windows.ps1",
        "build_desktop_unpacked_windows.ps1",
        "run_final_end_to_end_windows.ps1",
    ):
        text = (
            root
            / "scripts"
            / filename
        ).read_text(
            encoding="utf-8"
        )

        assert (
            "powershell_compat.ps1"
            in text
        )

        assert (
            "Assert-EvilTwinWindowsHost"
            in text
        )


def test_installer_cannot_call_nsis_before_frontend_e2e_and_release_preflight():
    root = resource_root()

    text = (
        root
        / "scripts"
        / "build_desktop_installer_windows.ps1"
    ).read_text(
        encoding="utf-8"
    )

    frontend_index = text.index(
        "validate_frontend_toolchain.ps1"
    )

    e2e_index = text.index(
        "validate_renderer_e2e.ps1"
    )

    preflight_index = text.index(
        "--target installer"
    )

    nsis_index = text.index(
        "npm run dist:win"
    )

    verify_index = text.index(
        "--target verify"
    )

    assert (
        frontend_index
        < e2e_index
        < preflight_index
        < nsis_index
        < verify_index
    )


def test_renderer_e2e_validator_honors_skip_install():
    root = resource_root()

    text = (
        root
        / "scripts"
        / "validate_renderer_e2e.ps1"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "[switch]$SkipInstall"
        in text
    )

    assert (
        "if (-not $SkipInstall)"
        in text
    )
