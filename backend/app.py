from __future__ import annotations

import sys
from threading import Lock

from fastapi import (
    FastAPI,
    HTTPException,
    status,
)
from fastapi.middleware.cors import CORSMiddleware

from desktop.windows.wlanapi_ctypes import (
    LocationAccessDeniedError,
    NativeWifiApiError,
    UnsupportedPlatformError,
)

from .dashboard import DashboardService
from .dashboard_router import router as dashboard_router
from .diagnostics import DiagnosticsService
from .diagnostics_router import router as diagnostics_router
from .db import (
    create_database_engine,
    create_session_factory,
)
from .history import HistoryService
from .history_router import router as history_router
from .inference import (
    FrozenDesktopInferenceService,
)
from .model_status import (
    ModelArtifactStatusService,
)
from .models import Base
from .persistence import (
    DatabaseStatusService,
    ScanPersistenceService,
)
from .runtime_store import RuntimeStore
from .scanner_service import ScannerService
from .settings import ApplicationSettingsService
from .settings_router import router as settings_router
from .schemas import (
    DatabaseStatusResponse,
    HealthResponse,
    ModelStatusResponse,
    NetworksResponse,
    ScanRequest,
    ScanResponse,
)


APP_VERSION = "1.4.0-step52"


def create_app(
    *,
    scanner_service:
        ScannerService
        | None = None,
    runtime_store:
        RuntimeStore
        | None = None,
    model_status_service:
        ModelArtifactStatusService
        | None = None,
    inference_service:
        FrozenDesktopInferenceService
        | None = None,
    database_url:
        str
        | None = None,
    persistence_service:
        ScanPersistenceService
        | None = None,
    database_status_service:
        DatabaseStatusService
        | None = None,
) -> FastAPI:
    app = FastAPI(
        title=(
            "Evil Twin Detector Local API"
        ),
        version=APP_VERSION,
        docs_url="/docs",
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "null",
        ],
        allow_credentials=False,
        allow_methods=[
            "GET",
            "POST",
            "PATCH",
            "OPTIONS",
        ],
        allow_headers=[
            "Content-Type",
        ],
    )

    scanner_service = (
        scanner_service
        if scanner_service
        is not None
        else ScannerService()
    )

    runtime_store = (
        runtime_store
        if runtime_store
        is not None
        else RuntimeStore()
    )

    model_status_service = (
        model_status_service
        if model_status_service
        is not None
        else ModelArtifactStatusService()
    )

    inference_service = (
        inference_service
        if inference_service
        is not None
        else FrozenDesktopInferenceService(
            model_status_service
        )
    )

    if (
        persistence_service
        is None
        or database_status_service
        is None
    ):
        engine = (
            create_database_engine(
                database_url
            )
        )

        # Alembic remains production schema authority.
        Base.metadata.create_all(
            engine
        )

        factory = (
            create_session_factory(
                engine
            )
        )

        persistence_service = (
            persistence_service
            or ScanPersistenceService(
                factory
            )
        )

        database_status_service = (
            database_status_service
            or DatabaseStatusService(
                engine,
                persistence_service,
            )
        )

    app.state.scanner_service = (
        scanner_service
    )

    app.state.runtime_store = (
        runtime_store
    )

    app.state.model_status_service = (
        model_status_service
    )

    app.state.inference_service = (
        inference_service
    )

    app.state.persistence_service = (
        persistence_service
    )

    app.state.database_status_service = (
        database_status_service
    )

    settings_service = (
        ApplicationSettingsService(
            persistence_service
            .session_factory,
            model_status_service,
        )
    )

    app.state.settings_service = (
        settings_service
    )

    history_service = HistoryService(
        persistence_service.session_factory
    )

    app.state.history_service = (
        history_service
    )

    dashboard_service = DashboardService(
        persistence_service.session_factory,
        history_service=history_service,
    )

    app.state.dashboard_service = (
        dashboard_service
    )

    diagnostics_service = DiagnosticsService(
        backend_version=APP_VERSION,
        scanner_service=scanner_service,
        model_status_service=model_status_service,
        database_status_service=database_status_service,
        settings_service=settings_service,
        history_service=history_service,
    )

    app.state.diagnostics_service = (
        diagnostics_service
    )

    app.include_router(
        history_router
    )

    app.include_router(
        dashboard_router
    )

    app.include_router(
        settings_router
    )

    app.include_router(
        diagnostics_router
    )

    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=[
            "system"
        ],
    )
    def health(
    ) -> HealthResponse:
        model = (
            model_status_service
            .get_status()
        )

        database = (
            database_status_service
            .get_status()
        )

        windows_supported = (
            sys.platform
            == "win32"
        )

        if windows_supported:
            scanner_status = (
                scanner_service.runtime_status
            )

        else:
            scanner_status = (
                "unsupported_platform"
            )

        return HealthResponse(
            status="ok",
            service=(
                "evil-twin-detector-backend"
            ),
            version=APP_VERSION,
            platform=sys.platform,
            windows_native_wifi_supported=(
                windows_supported
            ),
            scanner_status=(
                scanner_status
            ),
            model_status=(
                model.status
            ),
            database_status=(
                database[
                    "status"
                ]
            ),
        )

    @app.get(
        "/database",
        response_model=(
            DatabaseStatusResponse
        ),
        tags=[
            "system"
        ],
    )
    def database_status(
    ) -> DatabaseStatusResponse:
        return DatabaseStatusResponse(
            **database_status_service
            .get_status()
        )

    scan_execution_lock = Lock()

    app.state.scan_execution_lock = (
        scan_execution_lock
    )

    def _execute_scan(
        request: ScanRequest,
    ) -> ScanResponse:
        effective_request = (
            settings_service
            .resolve_scan_request(
                request
            )
        )

        try:
            raw_scan = (
                scanner_service
                .scan(
                    effective_request
                )
            )

        except LocationAccessDeniedError as exc:
            raise HTTPException(
                status_code=(
                    status
                    .HTTP_403_FORBIDDEN
                ),
                detail={
                    "code":
                        "location_access_denied",
                    "message":
                        str(
                            exc
                        ),
                    "settings_uri":
                        exc.settings_uri,
                },
            ) from exc

        except UnsupportedPlatformError as exc:
            raise HTTPException(
                status_code=(
                    status
                    .HTTP_501_NOT_IMPLEMENTED
                ),
                detail={
                    "code":
                        "unsupported_platform",
                    "message":
                        str(
                            exc
                        ),
                },
            ) from exc

        except NativeWifiApiError as exc:
            raise HTTPException(
                status_code=(
                    status
                    .HTTP_502_BAD_GATEWAY
                ),
                detail={
                    "code":
                        "native_wifi_api_error",
                    "function":
                        exc.function,
                    "win32_code":
                        exc.code,
                    "message":
                        str(
                            exc
                        ),
                },
            ) from exc

        outcome = (
            inference_service
            .analyze_scan(
                raw_scan
            )
        )

        analyzed_scan = (
            outcome.scan
        )

        try:
            persistence_service.persist_scan(
                analyzed_scan,
                model_descriptor=(
                    outcome.descriptor
                ),
            )

        except Exception as exc:
            raise HTTPException(
                status_code=(
                    status
                    .HTTP_500_INTERNAL_SERVER_ERROR
                ),
                detail={
                    "code":
                        "database_persist_failed",
                    "message": (
                        "Wi-Fi scan succeeded but "
                        "could not be persisted."
                    ),
                    "error":
                        str(
                            exc
                        ),
                },
            ) from exc

        runtime_store.set_latest_scan(
            analyzed_scan
        )

        return analyzed_scan

    @app.post(
        "/scan",
        response_model=ScanResponse,
        tags=[
            "wifi"
        ],
    )
    def scan(
        request: ScanRequest,
    ) -> ScanResponse:
        acquired = (
            scan_execution_lock
            .acquire(
                blocking=False
            )
        )

        if not acquired:
            raise HTTPException(
                status_code=(
                    status
                    .HTTP_409_CONFLICT
                ),
                detail={
                    "code":
                        "scan_in_progress",
                    "message": (
                        "Another Wi-Fi scan is already in progress."
                    ),
                },
            )

        try:
            return _execute_scan(
                request
            )
        finally:
            scan_execution_lock.release()


    @app.get(
        "/networks",
        response_model=(
            NetworksResponse
        ),
        tags=[
            "wifi"
        ],
    )
    def networks(
    ) -> NetworksResponse:
        latest = (
            runtime_store
            .get_latest_scan()
        )

        if latest is None:
            return NetworksResponse(
                has_scan=False,
                total_networks=0,
                networks=[],
            )

        return NetworksResponse(
            has_scan=True,
            scan_id=(
                latest.scan_id
            ),
            observed_at_utc=(
                latest
                .observed_at_utc
            ),
            total_networks=(
                latest
                .total_networks
            ),
            networks=(
                latest.networks
            ),
        )

    @app.get(
        "/model",
        response_model=(
            ModelStatusResponse
        ),
        tags=[
            "model"
        ],
    )
    def model_status(
    ) -> ModelStatusResponse:
        return (
            model_status_service
            .get_status()
        )

    return app


app = create_app()
