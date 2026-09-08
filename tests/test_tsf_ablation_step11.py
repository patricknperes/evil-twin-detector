from ml.evaluation.validate_tsf_ablation_step11 import (
    validate_step11,
)


def test_tsf_ablation_step11_report():
    report = validate_step11()

    assert (
        report[
            "primary_feature"
        ]
        == "tsf_reference_monotonic_violation"
    )

    assert (
        report[
            "decision"
        ][
            "status"
        ]
        == "ablation_only_pending_real_validation_and_scanner_availability"
    )
