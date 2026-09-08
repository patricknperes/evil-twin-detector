from pathlib import Path
import json


def test_eda_step1_report():
    root = Path(__file__).resolve().parents[1]
    path = (
        root
        / "reports"
        / "eda"
        / "eda_summary.json"
    )

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    assert data["phase"] == 3
    assert data["step"] == 1

    assert (
        data["datasets"]["mendeley"][
            "rows_normal"
        ]
        == 29990
    )

    assert (
        data["datasets"]["v2i"][
            "beacon_profile_80211n_rows"
        ]
        == 14812
    )

    assert (
        data["datasets"]["station"][
            "frames"
        ]
        == 97290
    )

    assert (
        data["datasets"]["longterm"][
            "flattened_ap_observations"
        ]
        > 1_000_000
    )
