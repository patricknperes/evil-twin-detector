from __future__ import annotations

from types import SimpleNamespace

from scripts import renderer_e2e


def test_run_renderer_e2e_resolves_npm_and_uses_utf8(
    tmp_path,
    monkeypatch,
):
    project = (
        tmp_path
        / "project"
    )

    (
        project
        / "frontend"
    ).mkdir(
        parents=True,
    )

    resolved_npm = (
        tmp_path
        / "npm.cmd"
    )

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        renderer_e2e,
        "inspect_renderer_e2e",
        lambda project_root: {
            "schema_version":
                renderer_e2e.SCHEMA_VERSION,
            "status":
                "READY_TO_EXECUTE",
            "source_ready":
                True,
            "dependencies_ready":
                True,
        },
    )

    monkeypatch.setattr(
        renderer_e2e.shutil,
        "which",
        lambda command: (
            str(
                resolved_npm
            )
            if command == "npm"
            else None
        ),
    )

    def fake_run(
        command,
        **kwargs,
    ):
        captured[
            "command"
        ] = command

        captured[
            "kwargs"
        ] = kwargs

        return SimpleNamespace(
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(
        renderer_e2e.subprocess,
        "run",
        fake_run,
    )

    result = (
        renderer_e2e.run_renderer_e2e(
            project,
            execute=True,
        )
    )

    assert (
        result[
            "status"
        ]
        == "PASSED"
    )

    assert captured[
        "command"
    ] == [
        str(
            resolved_npm
        ),
        "run",
        "e2e",
    ]

    assert captured[
        "kwargs"
    ][
        "encoding"
    ] == "utf-8"

    assert captured[
        "kwargs"
    ][
        "errors"
    ] == "replace"
