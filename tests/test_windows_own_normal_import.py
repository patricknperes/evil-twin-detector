import json

import pandas as pd

from desktop.windows.import_own_normal import (
    import_all_sessions,
    import_session,
    sha256_file,
    validate_source_session,
)


def _make_session(
    root,
    *,
    session_id="win-normal-test",
):
    session = root / session_id
    session.mkdir(
        parents=True
    )

    scans = []

    for index, tsf in enumerate([
        1000,
        2000,
        3000,
    ]):
        scans.append({
            "session_id":
                session_id,
            "scan_index":
                index,
            "captured_at_utc":
                f"2026-08-31T15:00:0{index}+00:00",
            "interfaces": [
                {
                    "interface": {
                        "guid":
                            "GUID-1"
                    },
                    "bss_entries": [
                        {
                            "ssid_hash":
                                "ssid-hash",
                            "bssid_hash":
                                "bssid-hash",
                            "ssid_not_broadcast":
                                False,
                            "rssi_dbm":
                                -50,
                            "link_quality":
                                90,
                            "beacon_interval_ms":
                                102.4,
                            "tsf_us":
                                tsf,
                            "host_timestamp_100ns":
                                tsf * 10,
                            "center_frequency_khz":
                                2437000,
                            "ds_parameter_channel":
                                6,
                            "security_type":
                                "WPA2_OR_NEWER",
                            "security_strength":
                                3,
                            "security_source":
                                "rsn_ie",
                            "ie_blob_size":
                                10,
                            "ie_parser_truncated":
                                False,
                            "native": {
                                "phy_id":
                                    1,
                                "bss_type":
                                    "infrastructure",
                                "phy_type":
                                    "ht",
                                "in_reg_domain":
                                    True,
                            },
                        }
                    ],
                }
            ],
        })

    scans_path = (
        session
        / "scans.jsonl"
    )

    scans_path.write_text(
        "\n".join(
            json.dumps(
                item,
                separators=(
                    ",",
                    ":",
                ),
            )
            for item in scans
        )
        + "\n",
        encoding="utf-8",
    )

    manifest = {
        "session_id":
            session_id,
        "label":
            0,
        "attack_present":
            False,
        "environment":
            "lab-a",
        "files": {
            "scans_sha256":
                sha256_file(
                    scans_path
                ),
        },
    }

    (
        session
        / "manifest.json"
    ).write_text(
        json.dumps(
            manifest
        ),
        encoding="utf-8",
    )

    # Must mirror validate_scans for this fixture.
    (
        session
        / "runtime_validation.json"
    ).write_text(
        json.dumps({
            "runtime_ready_for_own_normal_collection":
                True,
            "observation_count":
                3,
            "scan_count":
                3,
        }),
        encoding="utf-8",
    )

    return session


def test_import_session(
    tmp_path,
):
    session = _make_session(
        tmp_path
        / "raw"
    )

    result = import_session(
        session,
        tmp_path
        / "interim",
    )

    assert result.rows == 3
    assert result.scans == 3

    frame = pd.read_csv(
        tmp_path
        / "interim"
        / "win-normal-test"
        / "observations.csv.gz"
    )

    assert len(
        frame
    ) == 3

    assert set(
        frame[
            "source_dataset"
        ]
    ) == {
        "own_windows"
    }

    assert set(
        frame[
            "session_id"
        ]
    ) == {
        "win-normal-test"
    }

    assert "ssid" not in frame.columns
    assert "bssid" not in frame.columns
    assert "ssid_hash" in frame.columns
    assert "bssid_hash" in frame.columns


    import_manifest = json.loads(
        (
            tmp_path
            / "interim"
            / "win-normal-test"
            / "import_manifest.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert len(
        import_manifest[
            "interim_observations_sha256"
        ]
    ) == 64


def test_tampered_raw_rejected(
    tmp_path,
):
    session = _make_session(
        tmp_path
    )

    with (
        session
        / "scans.jsonl"
    ).open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            "{\"tampered\":true}\n"
        )

    try:
        validate_source_session(
            session
        )
    except ValueError as exc:
        assert "SHA-256" in str(
            exc
        )
    else:
        raise AssertionError(
            "Expected SHA-256 rejection."
        )


def test_no_sessions_is_valid(
    tmp_path,
):
    raw = (
        tmp_path
        / "raw"
    )

    raw.mkdir()

    result = import_all_sessions(
        raw,
        tmp_path
        / "interim",
    )

    assert result[
        "discovered_sessions"
    ] == 0

    assert result[
        "imported_sessions"
    ] == 0

    assert result[
        "real_data_available"
    ] is False


def test_interim_is_create_only(
    tmp_path,
):
    session = _make_session(
        tmp_path
        / "raw"
    )

    output = (
        tmp_path
        / "interim"
    )

    import_session(
        session,
        output,
    )

    try:
        import_session(
            session,
            output,
        )
    except FileExistsError:
        pass
    else:
        raise AssertionError(
            "Expected create-only interim."
        )


def test_batch_import_is_idempotent_when_existing_interim_matches_source(tmp_path):
    raw_root = tmp_path / "raw"
    interim_root = tmp_path / "interim"

    _make_session(
        raw_root,
        session_id="win-normal-idempotent",
    )

    from desktop.windows.import_own_normal import import_all_sessions

    first = import_all_sessions(raw_root, interim_root)
    assert first["imported_sessions"] == 1
    assert first["rejected_sessions"] == 0

    second = import_all_sessions(raw_root, interim_root)
    assert second["imported_sessions"] == 0
    assert second["skipped_existing_sessions"] == 1
    assert second["rejected_sessions"] == 0
    assert second["real_data_available"] is True
