from pathlib import Path
import json

import pandas as pd


def validate_step11(
    project_root=".",
):
    root = Path(
        project_root
    )

    report_path = (
        root
        / "reports"
        / "features"
        / "tsf_ablation_v1"
        / "tsf_ablation_step11.json"
    )

    report = json.loads(
        report_path.read_text(
            encoding="utf-8"
        )
    )

    assert report[
        "phase"
    ] == 4

    assert report[
        "step"
    ] == 11

    assert report[
        "status"
    ] == "ablation_only_not_promoted"

    assert (
        report[
            "decision"
        ][
            "promote_to_contextual_full_v1"
        ]
        is False
    )

    assert (
        report[
            "generator_audit"
        ][
            "all_source_rows_recovered"
        ]
        is True
    )

    coverage = report[
        "coverage"
    ]

    assert (
        coverage[
            "model_train_normal"
        ][
            "tsf_violation_count"
        ]
        == 0
    )

    assert (
        coverage[
            "validation_normal"
        ][
            "tsf_violation_count"
        ]
        == 0
    )

    assert (
        coverage[
            "test_normal"
        ][
            "tsf_violation_count"
        ]
        == 0
    )

    assert (
        coverage[
            "test_tsf_reset_synthetic"
        ][
            "tsf_violation_rate"
        ]
        == 1.0
    )

    return report


if __name__ == "__main__":
    validate_step11()
    print(
        "Fase 4 / Passo 11 validado."
    )
