from ml.evaluation.compare_phase4_models import (
    validate_phase4_step4,
)


def test_phase4_step4_comparison():
    report = validate_phase4_step4()

    assert (
        report[
            "model_diagnosis"
        ][
            "all_roc_auc_near_chance"
        ]
        is True
    )

    track = report[
        "feature_strategy"
    ][
        "TRACK_E_EVIL_TWIN_CONTEXT"
    ]

    assert (
        track["status"]
        == "next_feature_engineering_target"
    )
