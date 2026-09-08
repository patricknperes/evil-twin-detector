from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from desktop.windows.artifact_lineage import (
    validate_runtime_artifact_chain,
)
from desktop.windows.desktop_reference import (
    DESKTOP_FEATURES,
    transform_desktop_features,
)
from desktop.windows.scan_serialization import (
    hash_identifier,
    hash_ssid_identifier,
)

from .model_status import (
    ModelArtifactStatusService,
)
from .schemas import (
    NetworkAnalysisState,
    NetworkFeatureValues,
    ScanResponse,
)


def sha256_file(
    path: str | Path,
) -> str:
    digest = hashlib.sha256()

    with Path(
        path
    ).open(
        "rb"
    ) as handle:
        for block in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(
                block
            )

    return digest.hexdigest()


@dataclass(frozen=True)
class ModelRuntimeDescriptor:
    version_name: str
    algorithm: str
    feature_set_name: str
    reference_sha256: str
    scaler_sha256: str
    model_sha256: str
    threshold_sha256: str
    threshold: float

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "version_name":
                self.version_name,
            "algorithm":
                self.algorithm,
            "feature_set_name":
                self.feature_set_name,
            "reference_sha256":
                self.reference_sha256,
            "scaler_sha256":
                self.scaler_sha256,
            "model_sha256":
                self.model_sha256,
            "threshold_sha256":
                self.threshold_sha256,
            "threshold":
                self.threshold,
        }


@dataclass(frozen=True)
class RuntimeAnalysisOutcome:
    scan: ScanResponse
    descriptor: ModelRuntimeDescriptor | None
    runtime_status: str
    error: str | None = None


class FrozenDesktopInferenceService:
    """
    Product runtime for desktop_candidate_v1.

    It never fits, updates or calibrates any scientific artifact.
    Every artifact is loaded read-only from the frozen pipeline.
    """

    def __init__(
        self,
        artifact_status_service:
            ModelArtifactStatusService,
    ) -> None:
        self.artifact_status_service = (
            artifact_status_service
        )

        self._loaded_signature = None
        self._reference = None
        self._scaler = None
        self._model = None
        self._threshold = None
        self._descriptor = None

    def _signature(
        self,
    ):
        paths = (
            self.artifact_status_service
            .paths()
        )

        if not all(
            path.exists()
            for path in paths.values()
        ):
            return None

        return tuple(
            (
                name,
                path.stat().st_mtime_ns,
                path.stat().st_size,
            )
            for name, path
            in sorted(
                paths.items()
            )
        )

    def _validate_feature_contract(
        self,
        scaler,
        model,
    ) -> None:
        expected_count = len(
            DESKTOP_FEATURES
        )

        scaler_count = getattr(
            scaler,
            "n_features_in_",
            None,
        )

        model_count = getattr(
            model,
            "n_features_in_",
            None,
        )

        if (
            scaler_count
            is not None
            and int(
                scaler_count
            )
            != expected_count
        ):
            raise ValueError(
                "Scaler feature count diverges from desktop_candidate_v1."
            )

        if (
            model_count
            is not None
            and int(
                model_count
            )
            != expected_count
        ):
            raise ValueError(
                "Model feature count diverges from desktop_candidate_v1."
            )

        scaler_names = getattr(
            scaler,
            "feature_names_in_",
            None,
        )

        if (
            scaler_names
            is not None
            and list(
                scaler_names
            )
            != DESKTOP_FEATURES
        ):
            raise ValueError(
                "Scaler feature order diverges from desktop_candidate_v1."
            )

        model_names = getattr(
            model,
            "feature_names_in_",
            None,
        )

        if (
            model_names
            is not None
            and list(
                model_names
            )
            != DESKTOP_FEATURES
        ):
            raise ValueError(
                "Model feature order diverges from desktop_candidate_v1."
            )

    def _load(
        self,
    ) -> tuple[
        dict[str, object],
        object,
        object,
        float,
        ModelRuntimeDescriptor,
    ]:
        paths = (
            self.artifact_status_service
            .paths()
        )

        signature = self._signature()

        if signature is None:
            missing = [
                name
                for name, path
                in paths.items()
                if not path.exists()
            ]

            raise FileNotFoundError(
                "Missing runtime artifacts: "
                + ", ".join(
                    missing
                )
            )

        if (
            self._loaded_signature
            == signature
            and self._descriptor
            is not None
        ):
            return (
                self._reference,
                self._scaler,
                self._model,
                self._threshold,
                self._descriptor,
            )

        chain = (
            validate_runtime_artifact_chain(
                reference_path=(
                    paths[
                        "reference"
                    ]
                ),
                scaler_path=(
                    paths[
                        "scaler"
                    ]
                ),
                model_path=(
                    paths[
                        "model"
                    ]
                ),
                threshold_path=(
                    paths[
                        "threshold"
                    ]
                ),
            )
        )

        if not chain[
            "ready"
        ]:
            errors = (
                chain.get(
                    "errors",
                    [],
                )
                or chain.get(
                    "missing",
                    [],
                )
            )

            raise ValueError(
                "Runtime scientific artifact chain is invalid: "
                + ", ".join(
                    str(
                        error
                    )
                    for error
                    in errors
                )
            )

        reference = chain[
            "reference"
        ]

        scaler = joblib.load(
            paths[
                "scaler"
            ]
        )

        model = joblib.load(
            paths[
                "model"
            ]
        )

        threshold_payload = (
            chain[
                "threshold"
            ]
        )

        threshold = float(
            threshold_payload[
                "threshold"
            ]
        )

        if not np.isfinite(
            threshold
        ):
            raise ValueError(
                "Runtime threshold is not finite."
            )

        self._validate_feature_contract(
            scaler,
            model,
        )

        artifact_hashes = (
            chain[
                "actual_hashes"
            ]
        )

        combined = hashlib.sha256(
            "|".join(
                [
                    artifact_hashes[
                        "reference"
                    ],
                    artifact_hashes[
                        "scaler"
                    ],
                    artifact_hashes[
                        "model"
                    ],
                    artifact_hashes[
                        "threshold"
                    ],
                ]
            ).encode(
                "ascii"
            )
        ).hexdigest()

        descriptor = (
            ModelRuntimeDescriptor(
                version_name=(
                    "desktop_candidate_v1-"
                    + combined[
                        :16
                    ]
                ),
                algorithm=(
                    model.__class__.__name__
                ),
                feature_set_name=(
                    "desktop_candidate_v1"
                ),
                reference_sha256=(
                    artifact_hashes[
                        "reference"
                    ]
                ),
                scaler_sha256=(
                    artifact_hashes[
                        "scaler"
                    ]
                ),
                model_sha256=(
                    artifact_hashes[
                        "model"
                    ]
                ),
                threshold_sha256=(
                    artifact_hashes[
                        "threshold"
                    ]
                ),
                threshold=threshold,
            )
        )

        self._loaded_signature = (
            signature
        )

        self._reference = reference
        self._scaler = scaler
        self._model = model
        self._threshold = threshold
        self._descriptor = descriptor

        return (
            reference,
            scaler,
            model,
            threshold,
            descriptor,
        )

    def _not_available_scan(
        self,
        scan: ScanResponse,
        reason: str,
    ) -> ScanResponse:
        networks = [
            network.model_copy(
                update={
                    "analysis":
                        NetworkAnalysisState(
                            status=(
                                "not_available"
                            ),
                            suspicion_level=(
                                "unavailable"
                            ),
                            reason=reason,
                        )
                }
            )
            for network in scan.networks
        ]

        return scan.model_copy(
            update={
                "networks":
                    networks
            }
        )

    def analyze_scan(
        self,
        scan: ScanResponse,
    ) -> RuntimeAnalysisOutcome:
        artifact_status = (
            self.artifact_status_service
            .get_status()
        )

        if (
            artifact_status.status
            != "ready"
        ):
            reason = (
                "Desktop model is not ready. Missing: "
                + ", ".join(
                    artifact_status
                    .missing_artifacts
                )
            )

            return RuntimeAnalysisOutcome(
                scan=(
                    self._not_available_scan(
                        scan,
                        reason,
                    )
                ),
                descriptor=None,
                runtime_status=(
                    "not_ready"
                ),
            )

        try:
            (
                reference,
                scaler,
                model,
                threshold,
                descriptor,
            ) = self._load()

        except Exception as exc:
            return RuntimeAnalysisOutcome(
                scan=(
                    self._not_available_scan(
                        scan,
                        (
                            "Desktop model artifacts could not be loaded: "
                            + str(
                                exc
                            )
                        ),
                    )
                ),
                descriptor=None,
                runtime_status=(
                    "artifact_error"
                ),
                error=str(
                    exc
                ),
            )

        rows = []

        for network in scan.networks:
            rows.append({
                "ssid_hash": (
                    hash_ssid_identifier(
                        network.ssid
                    )
                    if (
                        network.ssid
                        and not network
                        .ssid_not_broadcast
                    )
                    else None
                ),
                "bssid_hash":
                    hash_identifier(
                        "bssid",
                        network.bssid,
                    ),
                "security_type":
                    network.security_type,
                "security_strength":
                    network.security_strength,
            })

        source = pd.DataFrame(
            rows
        )

        feature_frame = (
            transform_desktop_features(
                source,
                reference,
            )
        )

        analyses = [
            None
            for _ in scan.networks
        ]

        eligible_indices = []

        for index, feature_row in (
            feature_frame.iterrows()
        ):
            features = (
                NetworkFeatureValues(
                    ssid_bssid_count=(
                        None
                        if pd.isna(
                            feature_row[
                                "ssid_bssid_count"
                            ]
                        )
                        else float(
                            feature_row[
                                "ssid_bssid_count"
                            ]
                        )
                    ),
                    bssid_changed=(
                        None
                        if pd.isna(
                            feature_row[
                                "bssid_changed"
                            ]
                        )
                        else float(
                            feature_row[
                                "bssid_changed"
                            ]
                        )
                    ),
                    security_changed=(
                        None
                        if pd.isna(
                            feature_row[
                                "security_changed"
                            ]
                        )
                        else float(
                            feature_row[
                                "security_changed"
                            ]
                        )
                    ),
                    security_strength_delta=(
                        None
                        if pd.isna(
                            feature_row[
                                "security_strength_delta"
                            ]
                        )
                        else float(
                            feature_row[
                                "security_strength_delta"
                            ]
                        )
                    ),
                )
            )

            context_available = bool(
                feature_row[
                    "context_available"
                ]
            )

            feature_complete = bool(
                feature_row[
                    "feature_complete"
                ]
            )

            resolution = str(
                feature_row[
                    "context_resolution"
                ]
            )

            if (
                not context_available
                or not feature_complete
            ):
                analyses[
                    index
                ] = NetworkAnalysisState(
                    status=(
                        "insufficient_history"
                    ),
                    suspicion_level=(
                        "unavailable"
                    ),
                    context_available=(
                        context_available
                    ),
                    context_resolution=(
                        resolution
                    ),
                    feature_complete=(
                        feature_complete
                    ),
                    features=features,
                    model_version=(
                        descriptor
                        .version_name
                    ),
                    reason=(
                        "Histórico normal insuficiente para aplicar "
                        "desktop_candidate_v1 a esta rede."
                    ),
                )

            else:
                eligible_indices.append(
                    index
                )

                # Filled after batched inference.
                analyses[
                    index
                ] = (
                    features,
                    resolution,
                )

        if eligible_indices:
            X = feature_frame.loc[
                eligible_indices,
                DESKTOP_FEATURES,
            ].astype(
                float
            )

            inference_started = (
                time.perf_counter()
            )

            X_scaled = pd.DataFrame(
                scaler.transform(
                    X
                ),
                columns=DESKTOP_FEATURES,
                index=X.index,
            )

            scores = -np.asarray(
                model.decision_function(
                    X_scaled
                ),
                dtype=float,
            ).reshape(
                -1
            )

            inference_seconds = (
                time.perf_counter()
                - inference_started
            )

            inference_ms_each = (
                inference_seconds
                / len(
                    eligible_indices
                )
                * 1000.0
            )

            for position, index in enumerate(
                eligible_indices
            ):
                (
                    features,
                    resolution,
                ) = analyses[
                    index
                ]

                score = float(
                    scores[
                        position
                    ]
                )

                is_anomaly = (
                    score
                    > threshold
                )

                analyses[
                    index
                ] = NetworkAnalysisState(
                    status="ready",
                    anomaly_score=score,
                    threshold=threshold,
                    is_anomaly=(
                        is_anomaly
                    ),
                    suspicion_level=(
                        "high"
                        if is_anomaly
                        else "low"
                    ),
                    context_available=True,
                    context_resolution=(
                        resolution
                    ),
                    feature_complete=True,
                    features=features,
                    model_version=(
                        descriptor
                        .version_name
                    ),
                    inference_ms=float(
                        inference_ms_each
                    ),
                    reason=(
                        "Observação acima do threshold de anomalia."
                        if is_anomaly
                        else (
                            "Observação dentro do comportamento "
                            "esperado pelo modelo."
                        )
                    ),
                )

        analyzed_networks = [
            network.model_copy(
                update={
                    "analysis":
                        analyses[
                            index
                        ]
                }
            )
            for index, network
            in enumerate(
                scan.networks
            )
        ]

        analyzed_scan = (
            scan.model_copy(
                update={
                    "networks":
                        analyzed_networks
                }
            )
        )

        return RuntimeAnalysisOutcome(
            scan=analyzed_scan,
            descriptor=descriptor,
            runtime_status="ready",
        )
