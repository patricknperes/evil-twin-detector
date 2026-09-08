from __future__ import annotations

from pathlib import Path
import json


def load_phase4_comparison(
    project_root=".",
):
    path = (
        Path(
            project_root
        )
        / "reports"
        / "models"
        / "comparison"
        / "phase4_step4_comparison.json"
    )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def validate_phase4_step4(
    project_root=".",
):
    report = (
        load_phase4_comparison(
            project_root
        )
    )

    assert report[
        "phase"
    ] == 4

    assert report[
        "step"
    ] == 4

    models = {
        item["model"]
        for item in report[
            "model_comparison"
        ]
    }

    assert models == {
        "Isolation Forest",
        "One-Class SVM",
        "Autoencoder",
    }

    tracks = report[
        "feature_strategy"
    ]

    assert (
        "TRACK_G_GENERALIZATION"
        in tracks
    )

    assert (
        "TRACK_E_EVIL_TWIN_CONTEXT"
        in tracks
    )

    assert (
        "TRACK_D_DESKTOP"
        in tracks
    )

    forbidden = {
        "_rogue_type",
        "is_rogue",
    }

    contextual = tracks[
        "TRACK_E_EVIL_TWIN_CONTEXT"
    ]

    candidate_names = {
        item["feature"]
        for item in contextual[
            "candidate_derived_features"
        ]
    }

    assert not (
        forbidden
        & candidate_names
    )

    print(
        "Fase 4 / Passo 4 "
        "validado com sucesso."
    )

    return report


if __name__ == "__main__":
    validate_phase4_step4()
