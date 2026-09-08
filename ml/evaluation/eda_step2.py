from pathlib import Path
import json


REPORT_PATH = Path(
    "reports/eda/cross_dataset_comparison.json"
)


def validate_step2():
    report = json.loads(
        REPORT_PATH.read_text(
            encoding="utf-8"
        )
    )

    assert report["phase"] == 3
    assert report["step"] == 2

    compatibility = report[
        "feature_compatibility"
    ]

    assert (
        compatibility["rssi"]["status"]
        == "ALIGN_REQUIRED"
    )

    assert (
        compatibility[
            "beacon_interval"
        ]["status"]
        == "NOT_DIRECTLY_COMPATIBLE"
    )

    profiles = report[
        "revised_profiles"
    ]

    assert (
        "PROFILE_RSSI_HARMONIZED"
        in profiles
    )

    assert (
        profiles[
            "PROFILE_BEACON_OBSERVED"
        ]["status"]
        == "requires_feature_derivation"
    )

    print(
        "Fase 3 / Passo 2 "
        "validado com sucesso."
    )

    return report


if __name__ == "__main__":
    validate_step2()
