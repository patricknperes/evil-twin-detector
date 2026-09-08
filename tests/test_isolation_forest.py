import numpy as np

from sklearn.ensemble import IsolationForest

from ml.evaluation.anomaly_protocol import (
    to_anomaly_score,
    calibrate_threshold_from_normal_validation,
)


def test_isolation_forest_score_direction_and_threshold():
    rng = np.random.default_rng(
        123
    )

    train = rng.normal(
        0,
        1,
        size=(500, 2),
    )

    validation = rng.normal(
        0,
        1,
        size=(100, 2),
    )

    model = IsolationForest(
        n_estimators=50,
        random_state=123,
    )

    model.fit(
        train
    )

    score = to_anomaly_score(
        model.decision_function(
            validation
        ),
        higher_is_more_anomalous=False,
    )

    calibration = (
        calibrate_threshold_from_normal_validation(
            score,
            target_false_positive_rate=0.05,
        )
    )

    assert np.isfinite(
        calibration[
            "threshold"
        ]
    )

    assert (
        calibration[
            "validation_realized_false_positive_rate"
        ]
        <= 0.06
    )
