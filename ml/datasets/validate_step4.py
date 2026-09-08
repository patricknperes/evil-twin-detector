from pathlib import Path
import json

import pandas as pd

from ml.datasets.splits import (
    assert_no_group_leakage,
)


def validate_step4():
    root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    base = (
        root
        / "data"
        / "processed"
        / "splits"
        / "profile_rssi_temporal_5s"
    )

    manifest = json.loads(
        (
            base
            / "split_manifest.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert manifest[
        "phase"
    ] == 3

    assert manifest[
        "step"
    ] == 4

    normal = pd.read_csv(
        base
        / "normal_quality_all.csv.gz"
    )

    assert_no_group_leakage(
        normal
    )

    train = pd.read_csv(
        base
        / "train_balanced.csv.gz"
    )

    counts = (
        train[
            "source_dataset"
        ].value_counts()
    )

    assert (
        counts.nunique()
        == 1
    )

    attack = pd.read_csv(
        base
        / "test_attack_synthetic.csv.gz"
    )

    assert (
        attack["label"] == 1
    ).all()

    assert (
        normal["label"] == 0
    ).all()

    print(
        "Fase 3 / Passo 4 "
        "validado com sucesso."
    )


if __name__ == "__main__":
    validate_step4()
