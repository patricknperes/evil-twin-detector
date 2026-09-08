from pathlib import Path
import json


def validate_step13(
    project_root=".",
):
    root = Path(
        project_root
    )

    report = json.loads(
        (
            root
            / "reports"
            / "features"
            / "channel_semantics_v1"
            / "channel_semantics_step13.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert report[
        "phase"
    ] == 4

    assert report[
        "step"
    ] == 13

    assert report[
        "status"
    ] == "methodology_revision"

    assert (
        report[
            "generator_audit"
        ][
            "channel_changed_rows"
        ]
        == 5398
    )

    assert (
        report[
            "generator_audit"
        ][
            "ds_channel_changed_rows"
        ]
        == 0
    )

    assert (
        report[
            "decisions"
        ][
            "capture_advertised_mismatch"
        ][
            "status"
        ]
        == "rejected_as_primary_attack_feature"
    )

    assert (
        report[
            "decisions"
        ][
            "channel_changed_current_v1"
        ][
            "status"
        ]
        == "deprecated_for_primary_channel_semantics"
    )

    return report


if __name__ == "__main__":
    validate_step13()
    print(
        "Fase 4 / Passo 13 validado."
    )
