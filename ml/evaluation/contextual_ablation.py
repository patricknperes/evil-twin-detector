from __future__ import annotations

from pathlib import Path
import json


def load_step10_report(
    project_root=".",
):
    path = (
        Path(project_root)
        / "reports"
        / "models"
        / "contextual_ablation"
        / "contextual_ablation_step10.json"
    )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def validate_step10(
    project_root=".",
):
    report = load_step10_report(
        project_root
    )

    assert report["phase"] == 4
    assert report["step"] == 10

    assert (
        report[
            "ablation_feature_set"
        ][
            "features"
        ]
        == [
            "ssid_bssid_count",
            "channel_changed",
        ]
    )

    assert set(
        report[
            "ablation_feature_set"
        ][
            "removed_event_features"
        ]
    ) == {
        "bssid_changed",
        "security_changed",
        "security_strength_delta",
        "is_hidden",
    }

    assert set(
        report[
            "ablation_models"
        ]
    ) == {
        "Isolation Forest",
        "One-Class SVM",
        "Autoencoder",
    }

    return report


if __name__ == "__main__":
    validate_step10()
    print(
        "Fase 4 / Passo 10 validado."
    )
