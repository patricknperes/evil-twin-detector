from pathlib import Path
import json


def test_eda_step2_comparison():
    root = Path(__file__).resolve().parents[1]

    path = (
        root
        / "reports"
        / "eda"
        / "cross_dataset_comparison.json"
    )

    report = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    assert report["phase"] == 3
    assert report["step"] == 2

    assert (
        report[
            "feature_compatibility"
        ]["beacon_interval"]["status"]
        == "NOT_DIRECTLY_COMPATIBLE"
    )

    assert (
        report[
            "feature_compatibility"
        ]["ssid_bssid_identity"]["status"]
        == "GROUPING_ONLY"
    )

    assert (
        "PROFILE_RSSI_HARMONIZED"
        in report["revised_profiles"]
    )
