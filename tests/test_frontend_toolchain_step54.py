from __future__ import annotations

from types import SimpleNamespace

from scripts import frontend_toolchain


def test_run_resolves_executable_before_subprocess(
    tmp_path,
    monkeypatch,
):
    resolved_npm = (
        tmp_path
        / "npm.cmd"
    )

    captured: dict[str, object] = {}

    def fake_which(
        command: str,
    ) -> str | None:
        if command == "npm":
            return str(
                resolved_npm
            )

        return None

    def fake_run(
        command,
        **kwargs,
    ):
        captured["command"] = command
        captured["kwargs"] = kwargs

        return SimpleNamespace(
            returncode=0,
            stdout="10.9.8\n",
            stderr="",
        )

    monkeypatch.setattr(
        frontend_toolchain.shutil,
        "which",
        fake_which,
    )

    monkeypatch.setattr(
        frontend_toolchain.subprocess,
        "run",
        fake_run,
    )

    result = frontend_toolchain._run(
        [
            "npm",
            "--version",
        ],
        cwd=tmp_path,
        timeout=10,
    )

    assert result == {
        "ok": True,
        "returncode": 0,
        "reason": None,
    }

    assert captured[
        "command"
    ] == [
        str(
            resolved_npm
        ),
        "--version",
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


def test_run_reports_command_not_found(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        frontend_toolchain.shutil,
        "which",
        lambda command: None,
    )

    result = frontend_toolchain._run(
        [
            "npm",
            "--version",
        ],
        cwd=tmp_path,
        timeout=10,
    )

    assert result == {
        "ok": False,
        "returncode": None,
        "reason": "command_not_found",
    }
