from ml.evaluation.dataset_quality_report import build_decisions


def test_build_decisions():
    decisions = build_decisions(
        {
            "normal_rows": 29990,
            "synthetic_attack_rows": 37786,
        },
        {
            "beacon_profile_rows": 14812,
        },
        {
            "flattened_ap_observations":
                13471554,
        },
        {
            "frames": 97290,
        },
    )

    assert len(
        decisions[
            "main_normal_training"
        ]
    ) == 2

    assert (
        decisions[
            "attack_evaluation"
        ][0]["rows"]
        == 37786
    )
