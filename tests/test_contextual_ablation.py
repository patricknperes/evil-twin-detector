from ml.evaluation.contextual_ablation import (
    validate_step10,
)


def test_contextual_ablation_step10():
    report = validate_step10()

    assert (
        report[
            "current_operational_candidate"
        ][
            "model"
        ]
        == "One-Class SVM"
    )

    assert (
        report[
            "current_operational_candidate"
        ][
            "not_final"
        ]
        is True
    )
