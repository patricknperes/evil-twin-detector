from __future__ import annotations

from pathlib import Path

from desktop.windows.artifact_lineage import (
    validate_runtime_artifact_chain,
)

from .runtime_paths import runtime_artifact_paths
from .schemas import ModelStatusResponse


DESKTOP_FEATURES = [
    "ssid_bssid_count",
    "bssid_changed",
    "security_changed",
    "security_strength_delta",
]


class ModelArtifactStatusService:
    def __init__(
        self,
        *,
        project_root:
            str
            | Path
            | None = None,
    ) -> None:
        if project_root is None:
            paths = (
                runtime_artifact_paths()
            )

            self.reference_path = (
                paths["reference"]
            )
            self.scaler_path = (
                paths["scaler"]
            )
            self.model_path = (
                paths["model"]
            )
            self.threshold_path = (
                paths["threshold"]
            )
            return

        root = Path(
            project_root
        )

        self.reference_path = (
            root
            / "data"
            / "processed"
            / "desktop_candidate_v1"
            / "desktop_normal_reference.json"
        )

        self.scaler_path = (
            root
            / "ml"
            / "models"
            / "preprocessing"
            / "desktop_candidate_v1_standard_scaler.joblib"
        )

        self.model_path = (
            root
            / "ml"
            / "models"
            / "desktop_candidate_v1"
            / "ocsvm_v1"
            / "one_class_svm_desktop_candidate_v1.joblib"
        )

        self.threshold_path = (
            root
            / "ml"
            / "models"
            / "desktop_candidate_v1"
            / "ocsvm_v1"
            / "threshold.json"
        )

    def paths(
        self,
    ) -> dict[str, Path]:
        return {
            "reference":
                self.reference_path,
            "scaler":
                self.scaler_path,
            "model":
                self.model_path,
            "threshold":
                self.threshold_path,
        }

    def get_status(
        self,
    ) -> ModelStatusResponse:
        paths = self.paths()

        missing = [
            name
            for name, path
            in paths.items()
            if not path.exists()
        ]

        integrity_errors = []

        if not missing:
            integrity = (
                validate_runtime_artifact_chain(
                    reference_path=(
                        self.reference_path
                    ),
                    scaler_path=(
                        self.scaler_path
                    ),
                    model_path=(
                        self.model_path
                    ),
                    threshold_path=(
                        self.threshold_path
                    ),
                )
            )

            if not integrity[
                "ready"
            ]:
                integrity_errors = (
                    integrity.get(
                        "errors",
                        [],
                    )
                    or [
                        integrity[
                            "status"
                        ]
                    ]
                )

        ready = (
            not missing
            and not integrity_errors
        )

        reported_missing = list(
            missing
        )

        if integrity_errors:
            reported_missing.append(
                "artifact_lineage_integrity"
            )

        return ModelStatusResponse(
            status=(
                "ready"
                if ready
                else "not_ready"
            ),
            feature_set=DESKTOP_FEATURES,
            reference_path=str(
                self.reference_path
            ),
            scaler_path=str(
                self.scaler_path
            ),
            model_path=str(
                self.model_path
            ),
            threshold_path=str(
                self.threshold_path
            ),
            missing_artifacts=(
                reported_missing
            ),
            message=(
                "Frozen desktop reference/model artifacts are available "
                "and share one verified scientific lineage."
                if ready
                else (
                    "Desktop runtime artifacts are not available yet; "
                    "network analysis remains unavailable."
                    if missing
                    else (
                        "Desktop runtime artifact files exist, but their "
                        "scientific lineage is inconsistent: "
                        + ", ".join(
                            str(
                                error
                            )
                            for error
                            in integrity_errors
                        )
                    )
                )
            ),
        )
