import numpy as np

from ml.evaluation.anomaly_protocol import (
    to_anomaly_score,
    calibrate_threshold_from_normal_validation,
    evaluate_anomaly_detection,
)


def test_score_direction():
    raw = np.array([
        1.0,
        0.0,
        -1.0,
    ])

    score = to_anomaly_score(
        raw,
        higher_is_more_anomalous=False,
    )

    assert score.tolist() == [
        -1.0,
        -0.0,
        1.0,
    ]


def test_threshold_uses_normal_validation_quantile():
    scores = np.arange(
        100,
        dtype=float,
    )

    result = (
        calibrate_threshold_from_normal_validation(
            scores,
            target_false_positive_rate=0.05,
        )
    )

    assert result[
        "threshold"
    ] == 94.05

    assert result[
        "validation_realized_false_positive_rate"
    ] == 0.05


def test_binary_evaluation():
    metrics = (
        evaluate_anomaly_detection(
            normal_scores=[
                0.1,
                0.2,
            ],
            attack_scores=[
                0.8,
                0.9,
            ],
            threshold=0.5,
        )
    )

    assert metrics[
        "precision"
    ] == 1.0

    assert metrics[
        "recall"
    ] == 1.0

    assert metrics[
        "false_positive_rate"
    ] == 0.0

    assert metrics[
        "false_negative_rate"
    ] == 0.0
