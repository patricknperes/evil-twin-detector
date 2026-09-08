from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from .db import session_scope
from .models import (
    Detection,
    ModelVersion,
    NetworkFeatures,
    NetworkObservation,
    ScanSession,
)
from .schemas import (
    HistoryDetectionDetailResponse,
    HistoryDetectionListResponse,
    HistoryDetectionSummary,
    HistoryFeatureResponse,
    HistoryModelVersionListResponse,
    HistoryModelVersionResponse,
    HistoryObservationListResponse,
    HistoryObservationResponse,
    HistoryScanDetailResponse,
    HistoryScanListResponse,
    HistoryScanSummary,
    PaginationMeta,
)


class HistoryNotFoundError(LookupError):
    pass


class HistoryService:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    @staticmethod
    def _pagination(*, limit: int, offset: int, returned: int, total: int):
        return PaginationMeta(
            limit=limit,
            offset=offset,
            returned=returned,
            total=total,
        )

    @staticmethod
    def _feature_response(features: NetworkFeatures | None):
        if features is None:
            return None
        return HistoryFeatureResponse(
            ssid_bssid_count=features.ssid_bssid_count,
            bssid_changed=features.bssid_changed,
            security_changed=features.security_changed,
            security_strength_delta=features.security_strength_delta,
            context_available=features.context_available,
            context_resolution=features.context_resolution,
            feature_complete=features.feature_complete,
        )

    @staticmethod
    def _detection_summary(detection: Detection):
        return HistoryDetectionSummary(
            detection_id=detection.id,
            scan_id=detection.scan_session_id,
            observation_id=detection.network_observation_id,
            model_version_id=detection.model_version_id,
            anomaly_score=detection.anomaly_score,
            threshold=detection.threshold,
            is_anomaly=detection.is_anomaly,
            suspicion_level=detection.suspicion_level,
            reason=detection.reason,
            inference_ms=detection.inference_ms,
            created_at_utc=detection.created_at_utc,
        )

    @classmethod
    def _observation_response(cls, observation: NetworkObservation):
        detection = observation.detections[-1] if observation.detections else None
        try:
            supported_rates = json.loads(observation.supported_rates_json)
        except Exception:
            supported_rates = []
        return HistoryObservationResponse(
            observation_id=observation.id,
            scan_id=observation.scan_session_id,
            network_id=observation.network_id,
            interface_guid_hash=observation.interface_guid_hash,
            ssid_hash=observation.ssid_hash,
            bssid_hash=observation.bssid_hash,
            ssid_not_broadcast=observation.ssid_not_broadcast,
            rssi_dbm=observation.rssi_dbm,
            link_quality=observation.link_quality,
            beacon_interval_ms=observation.beacon_interval_ms,
            tsf_us=observation.tsf_us,
            host_timestamp_100ns=observation.host_timestamp_100ns,
            center_frequency_khz=observation.center_frequency_khz,
            ds_parameter_channel=observation.ds_parameter_channel,
            security_type=observation.security_type,
            security_strength=observation.security_strength,
            security_source=observation.security_source,
            phy_type=observation.phy_type,
            bss_type=observation.bss_type,
            supported_rates_mbps=supported_rates,
            features=cls._feature_response(observation.features),
            detection=(cls._detection_summary(detection) if detection else None),
        )

    @staticmethod
    def _model_response(model: ModelVersion, detection_count: int):
        return HistoryModelVersionResponse(
            model_version_id=model.id,
            version_name=model.version_name,
            algorithm=model.algorithm,
            feature_set_name=model.feature_set_name,
            reference_sha256=model.reference_sha256,
            scaler_sha256=model.scaler_sha256,
            model_sha256=model.model_sha256,
            threshold_sha256=model.threshold_sha256,
            threshold=model.threshold,
            active=model.active,
            created_at_utc=model.created_at_utc,
            notes=model.notes,
            detection_count=detection_count,
        )

    def _scan_summary(self, session, scan: ScanSession):
        feature_count = int(session.scalar(
            select(func.count()).select_from(NetworkFeatures)
            .join(NetworkObservation, NetworkObservation.id == NetworkFeatures.network_observation_id)
            .where(NetworkObservation.scan_session_id == scan.id)
        ) or 0)
        detection_count = int(session.scalar(
            select(func.count()).select_from(Detection)
            .where(Detection.scan_session_id == scan.id)
        ) or 0)
        anomaly_count = int(session.scalar(
            select(func.count()).select_from(Detection)
            .where(Detection.scan_session_id == scan.id, Detection.is_anomaly.is_(True))
        ) or 0)
        insufficient_count = int(session.scalar(
            select(func.count()).select_from(Detection)
            .where(Detection.scan_session_id == scan.id, Detection.is_anomaly.is_(None))
        ) or 0)
        return HistoryScanSummary(
            scan_id=scan.id,
            observed_at_utc=scan.observed_at_utc,
            negotiated_api_version=scan.negotiated_api_version,
            interface_count=scan.interface_count,
            total_networks=scan.total_networks,
            feature_count=feature_count,
            detection_count=detection_count,
            anomaly_count=anomaly_count,
            insufficient_history_count=insufficient_count,
        )

    def list_scans(self, *, limit: int, offset: int):
        with session_scope(self.session_factory) as session:
            total = int(session.scalar(
                select(func.count()).select_from(ScanSession)
            ) or 0)
            scans = session.scalars(
                select(ScanSession)
                .order_by(ScanSession.observed_at_utc.desc(), ScanSession.id.desc())
                .offset(offset).limit(limit)
            ).all()
            items = [self._scan_summary(session, scan) for scan in scans]
            return HistoryScanListResponse(
                pagination=self._pagination(
                    limit=limit, offset=offset, returned=len(items), total=total
                ),
                items=items,
            )

    def get_scan(self, scan_id: str):
        with session_scope(self.session_factory) as session:
            scan = session.get(ScanSession, scan_id)
            if scan is None:
                raise HistoryNotFoundError("Scan não encontrado.")
            observations = session.scalars(
                select(NetworkObservation)
                .where(NetworkObservation.scan_session_id == scan_id)
                .options(
                    selectinload(NetworkObservation.features),
                    selectinload(NetworkObservation.detections),
                )
                .order_by(NetworkObservation.id)
            ).all()
            return HistoryScanDetailResponse(
                scan=self._scan_summary(session, scan),
                observations=[self._observation_response(o) for o in observations],
            )

    def list_scan_observations(self, scan_id: str, *, limit: int, offset: int):
        with session_scope(self.session_factory) as session:
            if session.get(ScanSession, scan_id) is None:
                raise HistoryNotFoundError("Scan não encontrado.")
            total = int(session.scalar(
                select(func.count()).select_from(NetworkObservation)
                .where(NetworkObservation.scan_session_id == scan_id)
            ) or 0)
            observations = session.scalars(
                select(NetworkObservation)
                .where(NetworkObservation.scan_session_id == scan_id)
                .options(
                    selectinload(NetworkObservation.features),
                    selectinload(NetworkObservation.detections),
                )
                .order_by(NetworkObservation.id)
                .offset(offset).limit(limit)
            ).all()
            items = [self._observation_response(o) for o in observations]
            return HistoryObservationListResponse(
                pagination=self._pagination(
                    limit=limit, offset=offset, returned=len(items), total=total
                ),
                items=items,
            )

    def list_detections(
        self, *, limit: int, offset: int,
        is_anomaly: bool | None = None,
        suspicion_level: str | None = None,
        model_version_id: int | None = None,
    ):
        with session_scope(self.session_factory) as session:
            filters = []
            if is_anomaly is not None:
                filters.append(Detection.is_anomaly.is_(is_anomaly))
            if suspicion_level:
                filters.append(Detection.suspicion_level == suspicion_level)
            if model_version_id is not None:
                filters.append(Detection.model_version_id == model_version_id)

            count_stmt = select(func.count()).select_from(Detection)
            if filters:
                count_stmt = count_stmt.where(*filters)
            total = int(session.scalar(count_stmt) or 0)

            stmt = select(Detection).order_by(
                Detection.created_at_utc.desc(), Detection.id.desc()
            )
            if filters:
                stmt = stmt.where(*filters)
            detections = session.scalars(
                stmt.offset(offset).limit(limit)
            ).all()
            items = [self._detection_summary(d) for d in detections]
            return HistoryDetectionListResponse(
                pagination=self._pagination(
                    limit=limit, offset=offset, returned=len(items), total=total
                ),
                items=items,
            )

    def get_detection(self, detection_id: int):
        with session_scope(self.session_factory) as session:
            detection = session.scalar(
                select(Detection)
                .where(Detection.id == detection_id)
                .options(
                    selectinload(Detection.observation).selectinload(NetworkObservation.features),
                    selectinload(Detection.observation).selectinload(NetworkObservation.detections),
                    selectinload(Detection.model_version),
                )
            )
            if detection is None:
                raise HistoryNotFoundError("Detecção não encontrada.")

            model_response = None
            if detection.model_version is not None:
                count = int(session.scalar(
                    select(func.count()).select_from(Detection)
                    .where(Detection.model_version_id == detection.model_version_id)
                ) or 0)
                model_response = self._model_response(detection.model_version, count)

            return HistoryDetectionDetailResponse(
                detection=self._detection_summary(detection),
                observation=self._observation_response(detection.observation),
                model_version=model_response,
            )

    def list_models(self, *, limit: int, offset: int):
        with session_scope(self.session_factory) as session:
            total = int(session.scalar(
                select(func.count()).select_from(ModelVersion)
            ) or 0)
            models = session.scalars(
                select(ModelVersion)
                .order_by(ModelVersion.active.desc(), ModelVersion.created_at_utc.desc(), ModelVersion.id.desc())
                .offset(offset).limit(limit)
            ).all()
            items = []
            for model in models:
                count = int(session.scalar(
                    select(func.count()).select_from(Detection)
                    .where(Detection.model_version_id == model.id)
                ) or 0)
                items.append(self._model_response(model, count))
            return HistoryModelVersionListResponse(
                pagination=self._pagination(
                    limit=limit, offset=offset, returned=len(items), total=total
                ),
                items=items,
            )

    def get_model(self, model_version_id: int):
        with session_scope(self.session_factory) as session:
            model = session.get(ModelVersion, model_version_id)
            if model is None:
                raise HistoryNotFoundError("Versão de modelo não encontrada.")
            count = int(session.scalar(
                select(func.count()).select_from(Detection)
                .where(Detection.model_version_id == model.id)
            ) or 0)
            return self._model_response(model, count)
