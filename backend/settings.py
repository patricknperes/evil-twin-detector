from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)

from .db import session_scope
from .model_status import (
    ModelArtifactStatusService,
)
from .models import (
    ApplicationSettings,
)
from .schemas import (
    ApplicationSettingsConstraints,
    ApplicationSettingsResponse,
    ApplicationSettingsUpdate,
    ApplicationSettingsValues,
    ScanRequest,
    ScientificRuntimePolicy,
)


SETTINGS_ID = 1

DEFAULT_SETTINGS = {
    "request_fresh_scan":
        True,
    "scan_wait_seconds":
        4.2,
    "auto_scan_enabled":
        False,
    "auto_scan_interval_seconds":
        30.0,
    "history_page_size":
        25,
    "history_observation_page_size":
        50,
    "dashboard_recent_scans":
        5,
    "dashboard_recent_detections":
        5,
    "dashboard_trend_limit":
        30,
    "frontend_refresh_seconds":
        10,
    "show_technical_details":
        True,
    "high_anomaly_notifications":
        True,
}


class ApplicationSettingsService:
    """
    Product/application preferences only.

    No field in this service may mutate the frozen reference, scaler,
    OneClassSVM, threshold, or their artifact paths.
    """

    def __init__(
        self,
        session_factory,
        model_status_service:
            ModelArtifactStatusService,
    ) -> None:
        self.session_factory = (
            session_factory
        )
        self.model_status_service = (
            model_status_service
        )

    def _ensure(
        self,
        session,
    ) -> ApplicationSettings:
        row = session.get(
            ApplicationSettings,
            SETTINGS_ID,
        )

        if row is None:
            row = ApplicationSettings(
                id=SETTINGS_ID,
                **DEFAULT_SETTINGS,
            )
            session.add(
                row
            )
            session.flush()

        return row

    @staticmethod
    def _values(
        row: ApplicationSettings,
    ) -> ApplicationSettingsValues:
        return ApplicationSettingsValues(
            request_fresh_scan=(
                row.request_fresh_scan
            ),
            scan_wait_seconds=(
                row.scan_wait_seconds
            ),
            auto_scan_enabled=(
                row.auto_scan_enabled
            ),
            auto_scan_interval_seconds=(
                row
                .auto_scan_interval_seconds
            ),
            history_page_size=(
                row.history_page_size
            ),
            history_observation_page_size=(
                row
                .history_observation_page_size
            ),
            dashboard_recent_scans=(
                row.dashboard_recent_scans
            ),
            dashboard_recent_detections=(
                row
                .dashboard_recent_detections
            ),
            dashboard_trend_limit=(
                row.dashboard_trend_limit
            ),
            frontend_refresh_seconds=(
                row.frontend_refresh_seconds
            ),
            show_technical_details=(
                row.show_technical_details
            ),
            high_anomaly_notifications=(
                row
                .high_anomaly_notifications
            ),
            updated_at_utc=(
                row.updated_at_utc
            ),
        )

    def _response(
        self,
        values:
            ApplicationSettingsValues,
    ) -> ApplicationSettingsResponse:
        model = (
            self.model_status_service
            .get_status()
        )

        return ApplicationSettingsResponse(
            values=values,
            constraints=(
                ApplicationSettingsConstraints()
            ),
            model_status=(
                model.status
            ),
            missing_model_artifacts=(
                model.missing_artifacts
            ),
            scientific_policy=(
                ScientificRuntimePolicy()
            ),
        )

    def get_values(
        self,
    ) -> ApplicationSettingsValues:
        with session_scope(
            self.session_factory
        ) as session:
            row = self._ensure(
                session
            )
            return self._values(
                row
            )

    def get_response(
        self,
    ) -> ApplicationSettingsResponse:
        return self._response(
            self.get_values()
        )

    def update(
        self,
        patch:
            ApplicationSettingsUpdate,
    ) -> ApplicationSettingsResponse:
        changes = patch.model_dump(
            exclude_unset=True,
            exclude_none=True,
        )

        with session_scope(
            self.session_factory
        ) as session:
            row = self._ensure(
                session
            )

            for key, value in (
                changes.items()
            ):
                setattr(
                    row,
                    key,
                    value,
                )

            if changes:
                row.updated_at_utc = (
                    datetime.now(
                        timezone.utc
                    )
                )

            session.flush()

            values = self._values(
                row
            )

        return self._response(
            values
        )

    def reset(
        self,
    ) -> ApplicationSettingsResponse:
        with session_scope(
            self.session_factory
        ) as session:
            row = self._ensure(
                session
            )

            for key, value in (
                DEFAULT_SETTINGS.items()
            ):
                setattr(
                    row,
                    key,
                    value,
                )

            row.updated_at_utc = (
                datetime.now(
                    timezone.utc
                )
            )

            session.flush()

            values = self._values(
                row
            )

        return self._response(
            values
        )

    def resolve_scan_request(
        self,
        request:
            ScanRequest,
    ) -> ScanRequest:
        values = self.get_values()

        return ScanRequest(
            request_fresh_scan=(
                request
                .request_fresh_scan
                if request
                .request_fresh_scan
                is not None
                else values
                .request_fresh_scan
            ),
            scan_wait_seconds=(
                request
                .scan_wait_seconds
                if request
                .scan_wait_seconds
                is not None
                else values
                .scan_wait_seconds
            ),
            interface_guid=(
                request.interface_guid
            ),
        )
