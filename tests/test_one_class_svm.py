import numpy as np

from sklearn.svm import OneClassSVM

from ml.evaluation.anomaly_protocol import (
    to_anomaly_score,
    calibrate_threshold_from_normal_validation,
)


def test_one_class_svm_score_direction():
    rng = np.random.default_rng(
        321
    )

    train = rng.normal(
        0,
        1,
        size=(300, 2),
    )

    validation = rng.normal(
        0,
        1,
        size=(100, 2),
    )

    model = OneClassSVM(
        kernel="rbf",
        gamma="scale",
        nu=0.05,
    )

    model.fit(
        train
    )

    scores = to_anomaly_score(
        model.decision_function(
            validation
        ),
        higher_is_more_anomalous=False,
    )

    calibration = (
        calibrate_threshold_from_normal_validation(
            scores,
            target_false_positive_rate=0.05,
        )
    )

    assert np.isfinite(
        calibration[
            "threshold"
        ]
    )
