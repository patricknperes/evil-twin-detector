from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)

from sqlalchemy import (
    distinct,
    func,
    select,
)

from .db import session_scope
from .history import HistoryService
from .models import (
    Detection,
    ModelVersion,
    NetworkFeatures,
    NetworkObservation,
    ScanSession,
)
from .schemas import (
    DashboardMetrics,
    DashboardOverviewResponse,
    DashboardSystemStatus,
    DashboardTrendPoint,
    DashboardTrendsResponse,
    SuspicionDistribution,
)


class DashboardService:
    def __init__(
        self,
        session_factory,
        *,
        history_service:
            HistoryService
            | None = None,
    ) -> None:
        self.session_factory = (
            session_factory
        )

        self.history_service = (
            history_service
            or HistoryService(
                session_factory
            )
        )

    @staticmethod
    def _safe_rate(
        numerator: int,
        denominator: int,
    ) -> float:
        if denominator <= 0:
            return 0.0

        return float(
            numerator
            / denominator
        )

    def overview(
        self,
        *,
        backend_version: str,
        platform: str,
        scanner_status: str,
        database_status: str,
        model_status: str,
        recent_scans_limit: int,
        recent_detections_limit: int,
    ) -> DashboardOverviewResponse:
        with session_scope(
            self.session_factory
        ) as session:
            scan_count = int(
                session.scalar(
                    select(
                        func.count()
                    ).select_from(
                        ScanSession
                    )
                )
                or 0
            )

            observation_count = int(
                session.scalar(
                    select(
                        func.count()
                    ).select_from(
                        NetworkObservation
                    )
                )
                or 0
            )

            unique_network_count = int(
                session.scalar(
                    select(
                        func.count(
                            distinct(
                                NetworkObservation
                                .network_id
                            )
                        )
                    )
                )
                or 0
            )

            feature_count = int(
                session.scalar(
                    select(
                        func.count()
                    ).select_from(
                        NetworkFeatures
                    )
                )
                or 0
            )

            detection_count = int(
                session.scalar(
                    select(
                        func.count()
                    ).select_from(
                        Detection
                    )
                )
                or 0
            )

            anomaly_count = int(
                session.scalar(
                    select(
                        func.count()
                    )
                    .select_from(
                        Detection
                    )
                    .where(
                        Detection
                        .is_anomaly
                        .is_(
                            True
                        )
                    )
                )
                or 0
            )

            normal_count = int(
                session.scalar(
                    select(
                        func.count()
                    )
                    .select_from(
                        Detection
                    )
                    .where(
                        Detection
                        .is_anomaly
                        .is_(
                            False
                        )
                    )
                )
                or 0
            )

            insufficient_history_count = int(
                session.scalar(
                    select(
                        func.count()
                    )
                    .select_from(
                        Detection
                    )
                    .where(
                        Detection
                        .is_anomaly
                        .is_(
                            None
                        )
                    )
                )
                or 0
            )

            model_version_count = int(
                session.scalar(
                    select(
                        func.count()
                    ).select_from(
                        ModelVersion
                    )
                )
                or 0
            )

            distribution = {
                "low":
                    0,
                "medium":
                    0,
                "high":
                    0,
                "unavailable":
                    0,
            }

            distribution_rows = (
                session.execute(
                    select(
                        Detection
                        .suspicion_level,
                        func.count(
                            Detection.id
                        ),
                    )
                    .group_by(
                        Detection
                        .suspicion_level
                    )
                )
                .all()
            )

            for level, count in (
                distribution_rows
            ):
                if level in distribution:
                    distribution[
                        level
                    ] = int(
                        count
                    )

            latest_scan_at = (
                session.scalar(
                    select(
                        func.max(
                            ScanSession
                            .observed_at_utc
                        )
                    )
                )
            )

            latest_detection_at = (
                session.scalar(
                    select(
                        func.max(
                            Detection
                            .created_at_utc
                        )
                    )
                )
            )

            active_model = (
                session.scalar(
                    select(
                        ModelVersion
                    )
                    .where(
                        ModelVersion
                        .active
                        .is_(
                            True
                        )
                    )
                    .order_by(
                        ModelVersion
                        .created_at_utc
                        .desc(),
                        ModelVersion.id
                        .desc(),
                    )
                    .limit(
                        1
                    )
                )
            )

            active_model_response = None

            if active_model is not None:
                model_detection_count = int(
                    session.scalar(
                        select(
                            func.count()
                        )
                        .select_from(
                            Detection
                        )
                        .where(
                            Detection
                            .model_version_id
                            == active_model.id
                        )
                    )
                    or 0
                )

                active_model_response = (
                    self
                    .history_service
                    ._model_response(
                        active_model,
                        model_detection_count,
                    )
                )

        recent_scans = (
            self.history_service
            .list_scans(
                limit=recent_scans_limit,
                offset=0,
            )
            .items
        )

        recent_detections = (
            self.history_service
            .list_detections(
                limit=recent_detections_limit,
                offset=0,
            )
            .items
        )

        decided_count = (
            anomaly_count
            + normal_count
        )

        return DashboardOverviewResponse(
            generated_at_utc=(
                datetime.now(
                    timezone.utc
                )
            ),
            system=DashboardSystemStatus(
                backend_version=(
                    backend_version
                ),
                platform=platform,
                scanner_status=(
                    scanner_status
                ),
                database_status=(
                    database_status
                ),
                model_status=(
                    model_status
                ),
            ),
            metrics=DashboardMetrics(
                scan_count=scan_count,
                observation_count=(
                    observation_count
                ),
                unique_network_count=(
                    unique_network_count
                ),
                feature_count=(
                    feature_count
                ),
                detection_count=(
                    detection_count
                ),
                anomaly_count=(
                    anomaly_count
                ),
                normal_count=(
                    normal_count
                ),
                insufficient_history_count=(
                    insufficient_history_count
                ),
                model_version_count=(
                    model_version_count
                ),
                analysis_coverage_rate=(
                    self
                    ._safe_rate(
                        detection_count,
                        observation_count,
                    )
                ),
                anomaly_rate_among_decided=(
                    self
                    ._safe_rate(
                        anomaly_count,
                        decided_count,
                    )
                ),
            ),
            suspicion_distribution=(
                SuspicionDistribution(
                    **distribution
                )
            ),
            latest_scan_at_utc=(
                latest_scan_at
            ),
            latest_detection_at_utc=(
                latest_detection_at
            ),
            active_model=(
                active_model_response
            ),
            recent_scans=(
                recent_scans
            ),
            recent_detections=(
                recent_detections
            ),
        )

    def trends(
        self,
        *,
        limit: int,
    ) -> DashboardTrendsResponse:
        with session_scope(
            self.session_factory
        ) as session:
            scans = (
                session.scalars(
                    select(
                        ScanSession
                    )
                    .order_by(
                        ScanSession
                        .observed_at_utc
                        .desc(),
                        ScanSession.id
                        .desc(),
                    )
                    .limit(
                        limit
                    )
                )
                .all()
            )

            # For charts, selected recent records are returned
            # chronologically from oldest to newest.
            scans = list(
                reversed(
                    scans
                )
            )

            points = []

            for scan in scans:
                feature_count = int(
                    session.scalar(
                        select(
                            func.count()
                        )
                        .select_from(
                            NetworkFeatures
                        )
                        .join(
                            NetworkObservation,
                            (
                                NetworkObservation.id
                                == NetworkFeatures
                                .network_observation_id
                            ),
                        )
                        .where(
                            NetworkObservation
                            .scan_session_id
                            == scan.id
                        )
                    )
                    or 0
                )

                detection_count = int(
                    session.scalar(
                        select(
                            func.count()
                        )
                        .select_from(
                            Detection
                        )
                        .where(
                            Detection
                            .scan_session_id
                            == scan.id
                        )
                    )
                    or 0
                )

                anomaly_count = int(
                    session.scalar(
                        select(
                            func.count()
                        )
                        .select_from(
                            Detection
                        )
                        .where(
                            Detection
                            .scan_session_id
                            == scan.id,
                            Detection
                            .is_anomaly
                            .is_(
                                True
                            ),
                        )
                    )
                    or 0
                )

                normal_count = int(
                    session.scalar(
                        select(
                            func.count()
                        )
                        .select_from(
                            Detection
                        )
                        .where(
                            Detection
                            .scan_session_id
                            == scan.id,
                            Detection
                            .is_anomaly
                            .is_(
                                False
                            ),
                        )
                    )
                    or 0
                )

                insufficient_count = int(
                    session.scalar(
                        select(
                            func.count()
                        )
                        .select_from(
                            Detection
                        )
                        .where(
                            Detection
                            .scan_session_id
                            == scan.id,
                            Detection
                            .is_anomaly
                            .is_(
                                None
                            ),
                        )
                    )
                    or 0
                )

                points.append(
                    DashboardTrendPoint(
                        scan_id=scan.id,
                        observed_at_utc=(
                            scan
                            .observed_at_utc
                        ),
                        network_count=(
                            scan
                            .total_networks
                        ),
                        feature_count=(
                            feature_count
                        ),
                        detection_count=(
                            detection_count
                        ),
                        anomaly_count=(
                            anomaly_count
                        ),
                        normal_count=(
                            normal_count
                        ),
                        insufficient_history_count=(
                            insufficient_count
                        ),
                    )
                )

            return DashboardTrendsResponse(
                requested_limit=limit,
                returned=len(
                    points
                ),
                points=points,
            )
