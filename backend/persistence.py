from __future__ import annotations

import json

from sqlalchemy import (
    func,
    select,
    update,
)

from desktop.windows.scan_serialization import (
    hash_identifier,
    hash_ssid_identifier,
)

from .db import session_scope
from .inference import (
    ModelRuntimeDescriptor,
)
from .models import (
    Detection,
    ModelVersion,
    NetworkFeatures,
    NetworkObservation,
    ScanSession,
)
from .schemas import ScanResponse


def stable_hash(
    namespace: str,
    value: str,
) -> str:
    # Shared scientific/product hashing contract. SSID has a dedicated
    # canonical-text path so raw Windows bytes and product strings match.
    if namespace == "ssid":
        return hash_ssid_identifier(
            value
        )

    return hash_identifier(
        namespace,
        value,
    )


class ScanPersistenceService:
    def __init__(
        self,
        session_factory,
    ) -> None:
        self.session_factory = (
            session_factory
        )

    def _ensure_model_version(
        self,
        session,
        descriptor:
            ModelRuntimeDescriptor,
    ) -> ModelVersion:
        model_version = (
            session.scalar(
                select(
                    ModelVersion
                ).where(
                    ModelVersion
                    .version_name
                    == descriptor
                    .version_name
                )
            )
        )

        session.execute(
            update(
                ModelVersion
            )
            .where(
                ModelVersion.active
                .is_(
                    True
                )
            )
            .values(
                active=False
            )
        )

        if model_version is None:
            model_version = (
                ModelVersion(
                    version_name=(
                        descriptor
                        .version_name
                    ),
                    algorithm=(
                        descriptor
                        .algorithm
                    ),
                    feature_set_name=(
                        descriptor
                        .feature_set_name
                    ),
                    reference_sha256=(
                        descriptor
                        .reference_sha256
                    ),
                    model_sha256=(
                        descriptor
                        .model_sha256
                    ),
                    scaler_sha256=(
                        descriptor
                        .scaler_sha256
                    ),
                    threshold_sha256=(
                        descriptor
                        .threshold_sha256
                    ),
                    threshold=(
                        descriptor
                        .threshold
                    ),
                    active=True,
                    notes=(
                        "Frozen desktop_candidate_v1 "
                        "runtime artifact bundle."
                    ),
                )
            )

            session.add(
                model_version
            )

            session.flush()

        else:
            model_version.active = True
            model_version.algorithm = (
                descriptor.algorithm
            )
            model_version.feature_set_name = (
                descriptor
                .feature_set_name
            )
            model_version.reference_sha256 = (
                descriptor
                .reference_sha256
            )
            model_version.model_sha256 = (
                descriptor
                .model_sha256
            )
            model_version.scaler_sha256 = (
                descriptor
                .scaler_sha256
            )
            model_version.threshold_sha256 = (
                descriptor
                .threshold_sha256
            )
            model_version.threshold = (
                descriptor.threshold
            )

        return model_version

    def persist_scan(
        self,
        scan: ScanResponse,
        *,
        model_descriptor:
            ModelRuntimeDescriptor
            | None = None,
    ) -> dict[str, int]:
        with session_scope(
            self.session_factory
        ) as session:
            if (
                session.get(
                    ScanSession,
                    scan.scan_id,
                )
                is not None
            ):
                raise ValueError(
                    "scan_id já persistido: "
                    + scan.scan_id
                )

            scan_session = (
                ScanSession(
                    id=scan.scan_id,
                    observed_at_utc=(
                        scan.observed_at_utc
                    ),
                    negotiated_api_version=(
                        scan
                        .negotiated_api_version
                    ),
                    interface_count=(
                        scan.interface_count
                    ),
                    total_networks=(
                        scan.total_networks
                    ),
                )
            )

            session.add(
                scan_session
            )

            model_version = None

            if (
                model_descriptor
                is not None
            ):
                model_version = (
                    self
                    ._ensure_model_version(
                        session,
                        model_descriptor,
                    )
                )

            feature_count = 0
            detection_count = 0

            for network in scan.networks:
                observation = (
                    NetworkObservation(
                        scan_session_id=(
                            scan.scan_id
                        ),
                        network_id=(
                            network.network_id
                        ),
                        interface_guid_hash=(
                            stable_hash(
                                "interface-guid",
                                network
                                .interface_guid,
                            )
                        ),
                        ssid_hash=(
                            None
                            if (
                                network
                                .ssid_not_broadcast
                                or not network.ssid
                            )
                            else stable_hash(
                                "ssid",
                                network.ssid,
                            )
                        ),
                        bssid_hash=(
                            stable_hash(
                                "bssid",
                                network.bssid,
                            )
                        ),
                        ssid_not_broadcast=(
                            network
                            .ssid_not_broadcast
                        ),
                        rssi_dbm=(
                            network.rssi_dbm
                        ),
                        link_quality=(
                            network.link_quality
                        ),
                        beacon_interval_ms=(
                            network
                            .beacon_interval_ms
                        ),
                        tsf_us=(
                            network.tsf_us
                        ),
                        host_timestamp_100ns=(
                            network
                            .host_timestamp_100ns
                        ),
                        center_frequency_khz=(
                            network
                            .center_frequency_khz
                        ),
                        ds_parameter_channel=(
                            network
                            .ds_parameter_channel
                        ),
                        security_type=(
                            network
                            .security_type
                        ),
                        security_strength=(
                            network
                            .security_strength
                        ),
                        security_source=(
                            network
                            .security_source
                        ),
                        phy_type=(
                            network.phy_type
                        ),
                        bss_type=(
                            network.bss_type
                        ),
                        supported_rates_json=(
                            json.dumps(
                                network
                                .supported_rates_mbps,
                                separators=(
                                    ",",
                                    ":",
                                ),
                            )
                        ),
                    )
                )

                session.add(
                    observation
                )

                session.flush()

                analysis = (
                    network.analysis
                )

                if (
                    analysis.features
                    is not None
                ):
                    session.add(
                        NetworkFeatures(
                            network_observation_id=(
                                observation.id
                            ),
                            ssid_bssid_count=(
                                analysis
                                .features
                                .ssid_bssid_count
                            ),
                            bssid_changed=(
                                analysis
                                .features
                                .bssid_changed
                            ),
                            security_changed=(
                                analysis
                                .features
                                .security_changed
                            ),
                            security_strength_delta=(
                                analysis
                                .features
                                .security_strength_delta
                            ),
                            context_available=(
                                bool(
                                    analysis
                                    .context_available
                                )
                            ),
                            context_resolution=(
                                analysis
                                .context_resolution
                                or "unresolved"
                            ),
                            feature_complete=(
                                bool(
                                    analysis
                                    .feature_complete
                                )
                            ),
                        )
                    )

                    feature_count += 1

                if (
                    model_version
                    is not None
                    and analysis.status
                    in {
                        "ready",
                        "insufficient_history",
                    }
                ):
                    session.add(
                        Detection(
                            scan_session_id=(
                                scan.scan_id
                            ),
                            network_observation_id=(
                                observation.id
                            ),
                            model_version_id=(
                                model_version.id
                            ),
                            anomaly_score=(
                                analysis
                                .anomaly_score
                            ),
                            threshold=(
                                analysis
                                .threshold
                            ),
                            is_anomaly=(
                                analysis
                                .is_anomaly
                            ),
                            suspicion_level=(
                                analysis
                                .suspicion_level
                            ),
                            reason=(
                                analysis.reason
                            ),
                            inference_ms=(
                                analysis
                                .inference_ms
                            ),
                        )
                    )

                    detection_count += 1

            return {
                "scan_sessions":
                    1,
                "observations":
                    len(
                        scan.networks
                    ),
                "features":
                    feature_count,
                "detections":
                    detection_count,
                "model_versions_touched":
                    (
                        1
                        if model_version
                        is not None
                        else 0
                    ),
            }

    def _count(
        self,
        model,
    ) -> int:
        with session_scope(
            self.session_factory
        ) as session:
            return int(
                session.scalar(
                    select(
                        func.count()
                    ).select_from(
                        model
                    )
                )
                or 0
            )

    def count_scans(
        self,
    ) -> int:
        return self._count(
            ScanSession
        )

    def count_observations(
        self,
    ) -> int:
        return self._count(
            NetworkObservation
        )

    def count_features(
        self,
    ) -> int:
        return self._count(
            NetworkFeatures
        )

    def count_detections(
        self,
    ) -> int:
        return self._count(
            Detection
        )

    def count_model_versions(
        self,
    ) -> int:
        return self._count(
            ModelVersion
        )


class DatabaseStatusService:
    def __init__(
        self,
        engine,
        persistence_service:
            ScanPersistenceService,
    ) -> None:
        self.engine = engine
        self.persistence_service = (
            persistence_service
        )

    def get_status(
        self,
    ) -> dict[str, object]:
        try:
            return {
                "status":
                    "ready",
                "dialect":
                    self.engine.dialect.name,
                "scan_count":
                    self.persistence_service
                    .count_scans(),
                "observation_count":
                    self.persistence_service
                    .count_observations(),
                "feature_count":
                    self.persistence_service
                    .count_features(),
                "detection_count":
                    self.persistence_service
                    .count_detections(),
                "model_version_count":
                    self.persistence_service
                    .count_model_versions(),
            }

        except Exception as exc:
            return {
                "status":
                    "error",
                "dialect":
                    self.engine.dialect.name,
                "scan_count":
                    None,
                "observation_count":
                    None,
                "feature_count":
                    None,
                "detection_count":
                    None,
                "model_version_count":
                    None,
                "error":
                    str(
                        exc
                    ),
            }
