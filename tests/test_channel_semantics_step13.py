from ml.evaluation.validate_channel_semantics_step13 import (
    validate_step13,
)


def test_channel_semantics_step13():
    report = validate_step13()

    assert (
        report[
            "decisions"
        ][
            "contextual_full_v1"
        ][
            "status"
        ]
        == "superseded_pending_contextual_v2"
    )

    assert (
        report[
            "decisions"
        ][
            "advertised_channel_changed"
        ][
            "status"
        ]
        == "real_world_candidate_not_validated_by_channel_shift_synthetic"
    )
