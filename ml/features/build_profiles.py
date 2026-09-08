from pathlib import Path
import argparse
import json

from ml.features.beacon_profiles import (
    build_mendeley_beacon_1s,
    build_v2i_beacon_1s,
    build_rssi_temporal_5s,
)
from ml.features.io import (
    read_table,
    write_table,
)


def build_profiles(
    mendeley_normal_path,
    v2i_path,
    output_dir,
    mendeley_attack_path=None,
    preferred_format="parquet",
):
    output_dir = Path(
        output_dir
    )

    beacon_dir = (
        output_dir
        / "profile_beacon_1s"
    )

    temporal_dir = (
        output_dir
        / "profile_rssi_temporal_5s"
    )

    m_normal = read_table(
        mendeley_normal_path
    )

    v2i = read_table(
        v2i_path
    )

    m_beacon = (
        build_mendeley_beacon_1s(
            m_normal
        )
    )

    v_beacon = (
        build_v2i_beacon_1s(
            v2i
        )
    )

    outputs = {}

    outputs[
        "mendeley_normal_beacon_1s"
    ] = str(
        write_table(
            m_beacon,
            beacon_dir
            / "mendeley_normal",
            preferred_format,
        )
    )

    outputs[
        "v2i_normal_beacon_1s"
    ] = str(
        write_table(
            v_beacon,
            beacon_dir
            / "v2i_normal",
            preferred_format,
        )
    )

    outputs[
        "mendeley_normal_rssi_5s"
    ] = str(
        write_table(
            build_rssi_temporal_5s(
                m_beacon
            ),
            temporal_dir
            / "mendeley_normal",
            preferred_format,
        )
    )

    outputs[
        "v2i_normal_rssi_5s"
    ] = str(
        write_table(
            build_rssi_temporal_5s(
                v_beacon
            ),
            temporal_dir
            / "v2i_normal",
            preferred_format,
        )
    )

    if mendeley_attack_path:
        m_attack = read_table(
            mendeley_attack_path
        )

        attack_beacon = (
            build_mendeley_beacon_1s(
                m_attack
            )
        )

        outputs[
            "mendeley_attack_beacon_1s"
        ] = str(
            write_table(
                attack_beacon,
                beacon_dir
                / "mendeley_attack",
                preferred_format,
            )
        )

        outputs[
            "mendeley_attack_rssi_5s"
        ] = str(
            write_table(
                build_rssi_temporal_5s(
                    attack_beacon
                ),
                temporal_dir
                / "mendeley_attack",
                preferred_format,
            )
        )

    (
        output_dir
        / "feature_build_manifest.json"
    ).write_text(
        json.dumps(
            outputs,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return outputs


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--mendeley-normal",
        required=True,
    )

    parser.add_argument(
        "--mendeley-attack",
    )

    parser.add_argument(
        "--v2i",
        required=True,
    )

    parser.add_argument(
        "--output",
        default="data/processed",
    )

    parser.add_argument(
        "--format",
        choices=[
            "parquet",
            "csv.gz",
        ],
        default="parquet",
    )

    args = parser.parse_args()

    outputs = build_profiles(
        mendeley_normal_path=(
            args.mendeley_normal
        ),
        mendeley_attack_path=(
            args.mendeley_attack
        ),
        v2i_path=args.v2i,
        output_dir=args.output,
        preferred_format=args.format,
    )

    for name, path in (
        outputs.items()
    ):
        print(
            f"{name}: {path}"
        )


if __name__ == "__main__":
    main()
