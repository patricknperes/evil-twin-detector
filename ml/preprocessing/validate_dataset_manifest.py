from __future__ import annotations

from pathlib import Path
import argparse
import json


REQUIRED_DATASETS = {
    "mendeley_rogue_ap",
    "zenodo_v2i",
    "zenodo_longterm_wifi",
    "zenodo_station_management_frames",
    "own_collection",
}

REQUIRED_PROFILES = {
    "PROFILE_CORE",
    "PROFILE_BEACON",
    "PROFILE_SECURITY",
    "PROFILE_DESKTOP",
}


def validate_manifest(path):
    path = Path(path)

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        data["status"]
        == "approved"
    )

    assert REQUIRED_DATASETS.issubset(
        data["datasets"].keys()
    )

    assert REQUIRED_PROFILES.issubset(
        data[
            "experiment_profiles"
        ].keys()
    )

    mendeley = data[
        "datasets"
    ]["mendeley_rogue_ap"]

    assert (
        mendeley[
            "normal_profile"
        ]["is_synthetic"]
        is False
    )

    assert (
        mendeley[
            "attack_profile"
        ]["is_synthetic"]
        is True
    )

    assert (
        mendeley[
            "attack_profile"
        ]["usage"]
        == "auxiliary_attack_test_only"
    )

    desktop = data[
        "experiment_profiles"
    ]["PROFILE_DESKTOP"]

    assert (
        desktop["status"]
        == "candidate_until_windows_scanner_validation"
    )

    ids = [
        experiment["id"]
        for experiment in data[
            "approved_experimental_sequence"
        ]
    ]

    assert ids == [
        "E1",
        "E2",
        "E3",
        "E4",
        "E5",
        "E6",
    ]

    print(
        "Manifesto validado com sucesso."
    )

    return data


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--manifest",
        default=(
            "config/"
            "dataset_manifest.json"
        ),
    )

    args = parser.parse_args()

    validate_manifest(
        args.manifest
    )


if __name__ == "__main__":
    main()
