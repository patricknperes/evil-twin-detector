from __future__ import annotations

import json

from desktop.implementation_freeze import (
    compute_implementation_snapshot,
    verify_implementation_snapshot,
)


def test_implementation_snapshot_detects_source_mutation(tmp_path):
    project = tmp_path / "project"
    (project / "backend").mkdir(parents=True)
    (project / "backend" / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (project / "README.md").write_text("review\n", encoding="utf-8")

    snapshot = compute_implementation_snapshot(project)
    snapshot_path = project / "snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")

    ready = verify_implementation_snapshot(project, snapshot_path)
    assert ready["ready"] is True

    (project / "backend" / "module.py").write_text("VALUE = 2\n", encoding="utf-8")

    changed = verify_implementation_snapshot(project, snapshot_path)
    assert changed["ready"] is False
    assert "backend/module.py" in changed["changed"]


def test_implementation_snapshot_ignores_reports_and_data(tmp_path):
    project = tmp_path / "project"
    (project / "backend").mkdir(parents=True)
    (project / "backend" / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (project / "reports").mkdir(parents=True)
    (project / "data" / "raw").mkdir(parents=True)

    before = compute_implementation_snapshot(project)

    (project / "reports" / "run.json").write_text("{}", encoding="utf-8")
    (project / "data" / "raw" / "capture.bin").write_bytes(b"real-data")

    after = compute_implementation_snapshot(project)
    assert before["tree_sha256"] == after["tree_sha256"]

def test_implementation_snapshot_ignores_generated_desktop_model_artifacts_but_tracks_model_source(
    tmp_path,
):
    project = tmp_path / "project"

    model_source = (
        project
        / "ml"
        / "models"
        / "autoencoder"
        / "model.py"
    )
    model_source.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    model_source.write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )

    before = compute_implementation_snapshot(
        project
    )

    generated_files = [
        (
            project
            / "ml"
            / "models"
            / "desktop_candidate_v1"
            / "ocsvm_v1"
            / "one_class_svm_desktop_candidate_v1.joblib"
        ),
        (
            project
            / "ml"
            / "models"
            / "desktop_candidate_v1"
            / "ocsvm_v1"
            / "threshold.json"
        ),
        (
            project
            / "ml"
            / "models"
            / "preprocessing"
            / "desktop_candidate_v1_standard_scaler.joblib"
        ),
        (
            project
            / "ml"
            / "models"
            / "preprocessing"
            / "desktop_candidate_v1_standard_scaler.json"
        ),
    ]

    for generated in generated_files:
        generated.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        generated.write_bytes(
            b"generated-artifact"
        )

    after_generated = (
        compute_implementation_snapshot(
            project
        )
    )

    assert (
        before["tree_sha256"]
        == after_generated["tree_sha256"]
    )

    model_source.write_text(
        "VALUE = 2\n",
        encoding="utf-8",
    )

    after_source_change = (
        compute_implementation_snapshot(
            project
        )
    )

    assert (
        after_source_change["tree_sha256"]
        != after_generated["tree_sha256"]
    )

