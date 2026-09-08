from pathlib import Path
import json

import pandas as pd


FORBIDDEN_X_COLUMNS = {
    "source_dataset",
    "session_id",
    "network_identity_id",
    "network_group_id",
    "window_start_ms",
    "split",
    "split_group_type",
    "split_group_id",
    "label",
    "attack_type",
    "is_synthetic",
}


def validate_step5():
    root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    base = (
        root
        / "data"
        / "processed"
        / "ml_ready"
        / "profile_rssi_temporal_5s"
    )

    manifest = json.loads(
        (
            base
            / "ml_matrix_manifest.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert manifest[
        "phase"
    ] == 3

    assert manifest[
        "step"
    ] == 5

    assert set(
        manifest[
            "feature_sets"
        ].keys()
    ) == {
        "conservative_v1",
        "complete_v1",
    }

    for feature_set in [
        "conservative_v1",
        "complete_v1",
    ]:
        for split in [
            "train_full",
            "train_balanced",
            "validation",
            "test_normal",
            "test_attack_synthetic",
        ]:
            folder = (
                base
                / feature_set
                / split
            )

            X = pd.read_csv(
                folder
                / "X.csv.gz"
            )

            y = pd.read_csv(
                folder
                / "y.csv.gz"
            )

            metadata = pd.read_csv(
                folder
                / "metadata.csv.gz"
            )

            assert len(X) == len(y)
            assert len(X) == len(metadata)

            assert not (
                FORBIDDEN_X_COLUMNS
                & set(X.columns)
            )

            assert not X.isna().any().any()

    print(
        "Fase 3 / Passo 5 "
        "validado com sucesso."
    )


if __name__ == "__main__":
    validate_step5()
