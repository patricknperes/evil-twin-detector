from __future__ import annotations

from pathlib import Path
import argparse
import json
import random
import time

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import (
    DataLoader,
    TensorDataset,
)

from ml.models.autoencoder.model import (
    Autoencoder,
    reconstruction_error,
)
from ml.evaluation.anomaly_protocol import (
    calibrate_threshold_from_normal_validation,
    evaluate_anomaly_detection,
    evaluate_normal_only,
)


SEED = 20260831


def load_x(
    base,
    split,
):
    return pd.read_csv(
        Path(base)
        / split
        / "X.csv.gz"
    )


def tensor_from_df(
    df,
):
    return torch.tensor(
        df.to_numpy(
            dtype=np.float32
        ),
        dtype=torch.float32,
    )


def train_autoencoder(
    scaled_base,
    output_model,
    epochs=100,
    batch_size=64,
    learning_rate=0.001,
    target_fpr=0.05,
):
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    X_train = load_x(
        scaled_base,
        "train_balanced",
    )

    X_validation = load_x(
        scaled_base,
        "validation",
    )

    X_test_normal = load_x(
        scaled_base,
        "test_normal",
    )

    X_test_attack = load_x(
        scaled_base,
        "test_attack_synthetic",
    )

    model = Autoencoder()

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=learning_rate,
    )

    criterion = nn.MSELoss()

    train_tensor = tensor_from_df(
        X_train
    )

    loader = DataLoader(
        TensorDataset(
            train_tensor,
            train_tensor,
        ),
        batch_size=batch_size,
        shuffle=True,
    )

    start = time.perf_counter()

    for _ in range(
        epochs
    ):
        model.train()

        for batch, target in loader:
            optimizer.zero_grad(
                set_to_none=True
            )

            reconstructed = model(
                batch
            )

            loss = criterion(
                reconstructed,
                target,
            )

            loss.backward()
            optimizer.step()

    fit_seconds = (
        time.perf_counter()
        - start
    )

    validation_scores = (
        reconstruction_error(
            model,
            tensor_from_df(
                X_validation
            ),
        )
        .numpy()
    )

    calibration = (
        calibrate_threshold_from_normal_validation(
            validation_scores,
            target_false_positive_rate=target_fpr,
        )
    )

    threshold = calibration[
        "threshold"
    ]

    normal_scores = (
        reconstruction_error(
            model,
            tensor_from_df(
                X_test_normal
            ),
        )
        .numpy()
    )

    attack_scores = (
        reconstruction_error(
            model,
            tensor_from_df(
                X_test_attack
            ),
        )
        .numpy()
    )

    output_model = Path(
        output_model
    )

    output_model.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    torch.save(
        {
            "model_state_dict":
                model.state_dict(),
            "threshold":
                threshold,
        },
        output_model,
    )

    return {
        "fit_seconds":
            fit_seconds,
        "threshold":
            threshold,
        "calibration":
            calibration,
        "test_normal":
            evaluate_normal_only(
                normal_scores,
                threshold,
            ),
        "test_binary":
            evaluate_anomaly_detection(
                normal_scores,
                attack_scores,
                threshold,
            ),
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--scaled-base",
        default=(
            "data/processed/ml_ready/"
            "profile_rssi_temporal_5s/"
            "conservative_v2_scaled"
        ),
    )

    parser.add_argument(
        "--output-model",
        default=(
            "ml/models/autoencoder/"
            "autoencoder_conservative_v2.pt"
        ),
    )

    args = parser.parse_args()

    result = train_autoencoder(
        args.scaled_base,
        args.output_model,
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
