import numpy as np
import pandas as pd

from ml.training.anomaly_pipeline import (
    fit_scaler_train_only,
    transform_with_scaler,
)


def test_scaler_fit_train_only_behavior():
    train = pd.DataFrame({
        "a": [
            0.0,
            2.0,
        ],
        "b": [
            -1.0,
            1.0,
        ],
    })

    test = pd.DataFrame({
        "a": [
            100.0,
        ],
        "b": [
            100.0,
        ],
    })

    scaler = (
        fit_scaler_train_only(
            train
        )
    )

    transformed_train = (
        transform_with_scaler(
            scaler,
            train,
        )
    )

    transformed_test = (
        transform_with_scaler(
            scaler,
            test,
        )
    )

    assert np.allclose(
        transformed_train.mean(),
        [0.0, 0.0],
    )

    # Se o scaler tivesse sido refitado no teste,
    # uma linha única viraria 0. O valor deve permanecer grande.
    assert (
        transformed_test.iloc[
            0
        ]["a"]
        > 10
    )
