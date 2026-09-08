from __future__ import annotations

import numpy as np

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)


def to_anomaly_score(
    raw_scores,
    higher_is_more_anomalous,
):
    """
    Padroniza todos os modelos para:

        anomaly_score MAIOR
        =
        mais anômalo

    Exemplos:

    Isolation Forest decision_function:
        maior = mais normal
        -> higher_is_more_anomalous=False

    One-Class SVM decision_function:
        maior = mais normal
        -> higher_is_more_anomalous=False

    Autoencoder reconstruction error:
        maior = mais anômalo
        -> higher_is_more_anomalous=True
    """
    scores = np.asarray(
        raw_scores,
        dtype=float,
    )

    if higher_is_more_anomalous:
        return scores

    return -scores


def calibrate_threshold_from_normal_validation(
    anomaly_scores,
    target_false_positive_rate=0.05,
):
    """
    Calibra threshold usando SOMENTE validação normal.

    Se target FPR = 0.05:
        threshold = percentil 95 dos anomaly scores normais.

    Nenhuma amostra de ataque é usada para escolher threshold.
    """
    scores = np.asarray(
        anomaly_scores,
        dtype=float,
    )

    if scores.ndim != 1:
        scores = scores.reshape(-1)

    if len(scores) == 0:
        raise ValueError(
            "Validation scores vazios."
        )

    if not (
        0.0
        < target_false_positive_rate
        < 1.0
    ):
        raise ValueError(
            "target_false_positive_rate "
            "deve estar entre 0 e 1."
        )

    if not np.isfinite(
        scores
    ).all():
        raise ValueError(
            "Scores contêm NaN/inf."
        )

    quantile = (
        1.0
        - target_false_positive_rate
    )

    threshold = float(
        np.quantile(
            scores,
            quantile,
            method="linear",
        )
    )

    predicted_anomaly = (
        scores > threshold
    )

    realized_fpr = float(
        predicted_anomaly.mean()
    )

    return {
        "threshold":
            threshold,
        "target_false_positive_rate":
            float(
                target_false_positive_rate
            ),
        "validation_realized_false_positive_rate":
            realized_fpr,
        "validation_rows":
            int(
                len(scores)
            ),
        "quantile":
            float(
                quantile
            ),
    }


def predict_from_anomaly_score(
    anomaly_scores,
    threshold,
):
    scores = np.asarray(
        anomaly_scores,
        dtype=float,
    )

    return (
        scores > float(
            threshold
        )
    ).astype(int)


def evaluate_anomaly_detection(
    normal_scores,
    attack_scores,
    threshold,
):
    """
    Avaliação binária final:

        normal = 0
        ataque/anomalia = 1

    Threshold deve ter sido congelado antes desta chamada.
    """
    normal_scores = np.asarray(
        normal_scores,
        dtype=float,
    ).reshape(-1)

    attack_scores = np.asarray(
        attack_scores,
        dtype=float,
    ).reshape(-1)

    if (
        len(normal_scores) == 0
        or len(attack_scores) == 0
    ):
        raise ValueError(
            "Normal e attack scores "
            "devem ser não vazios."
        )

    scores = np.concatenate([
        normal_scores,
        attack_scores,
    ])

    y_true = np.concatenate([
        np.zeros(
            len(
                normal_scores
            ),
            dtype=int,
        ),
        np.ones(
            len(
                attack_scores
            ),
            dtype=int,
        ),
    ])

    y_pred = (
        predict_from_anomaly_score(
            scores,
            threshold,
        )
    )

    matrix = confusion_matrix(
        y_true,
        y_pred,
        labels=[0, 1],
    )

    tn, fp, fn, tp = (
        matrix.ravel()
    )

    fpr = (
        fp / (
            fp + tn
        )
        if (
            fp + tn
        ) > 0
        else 0.0
    )

    fnr = (
        fn / (
            fn + tp
        )
        if (
            fn + tp
        ) > 0
        else 0.0
    )

    return {
        "threshold":
            float(
                threshold
            ),
        "normal_rows":
            int(
                len(
                    normal_scores
                )
            ),
        "attack_rows":
            int(
                len(
                    attack_scores
                )
            ),
        "accuracy":
            float(
                accuracy_score(
                    y_true,
                    y_pred,
                )
            ),
        "precision":
            float(
                precision_score(
                    y_true,
                    y_pred,
                    zero_division=0,
                )
            ),
        "recall":
            float(
                recall_score(
                    y_true,
                    y_pred,
                    zero_division=0,
                )
            ),
        "f1":
            float(
                f1_score(
                    y_true,
                    y_pred,
                    zero_division=0,
                )
            ),
        "roc_auc":
            float(
                roc_auc_score(
                    y_true,
                    scores,
                )
            ),
        "false_positive_rate":
            float(
                fpr
            ),
        "false_negative_rate":
            float(
                fnr
            ),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
    }


def evaluate_normal_only(
    normal_scores,
    threshold,
):
    """
    Útil para validação ou ambientes normais não vistos.
    """
    scores = np.asarray(
        normal_scores,
        dtype=float,
    ).reshape(-1)

    predicted = (
        predict_from_anomaly_score(
            scores,
            threshold,
        )
    )

    return {
        "rows":
            int(
                len(scores)
            ),
        "false_positive_count":
            int(
                predicted.sum()
            ),
        "false_positive_rate":
            float(
                predicted.mean()
            ),
        "score_mean":
            float(
                scores.mean()
            ),
        "score_median":
            float(
                np.median(
                    scores
                )
            ),
        "score_min":
            float(
                scores.min()
            ),
        "score_max":
            float(
                scores.max()
            ),
    }
