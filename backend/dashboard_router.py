from __future__ import annotations

import sys

from fastapi import (
    APIRouter,
    Query,
    Request,
)

from .schemas import (
    DashboardOverviewResponse,
    DashboardTrendsResponse,
)


router = APIRouter(
    prefix="/dashboard",
    tags=[
        "dashboard"
    ],
)


def _dashboard(
    request: Request,
):
    return (
        request.app.state
        .dashboard_service
    )


@router.get(
    "/overview",
    response_model=(
        DashboardOverviewResponse
    ),
)
def overview(
    request: Request,
    recent_scans: int | None = Query(
        default=None,
        ge=0,
        le=20,
    ),
    recent_detections: int | None = Query(
        default=None,
        ge=0,
        le=20,
    ),
):
    app = request.app

    model = (
        app.state
        .model_status_service
        .get_status()
    )

    database = (
        app.state
        .database_status_service
        .get_status()
    )

    scanner_service = (
        app.state
        .scanner_service
    )

    settings = (
        app.state
        .settings_service
        .get_values()
    )

    if recent_scans is None:
        recent_scans = (
            settings
            .dashboard_recent_scans
        )

    if recent_detections is None:
        recent_detections = (
            settings
            .dashboard_recent_detections
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

    return _dashboard(
        request
    ).overview(
        backend_version=(
            app.version
        ),
        platform=sys.platform,
        scanner_status=(
            scanner_status
        ),
        database_status=(
            database[
                "status"
            ]
        ),
        model_status=(
            model.status
        ),
        recent_scans_limit=(
            recent_scans
        ),
        recent_detections_limit=(
            recent_detections
        ),
    )


@router.get(
    "/trends",
    response_model=(
        DashboardTrendsResponse
    ),
)
def trends(
    request: Request,
    limit: int | None = Query(
        default=None,
        ge=1,
        le=100,
    ),
):
    if limit is None:
        limit = (
            request.app.state
            .settings_service
            .get_values()
            .dashboard_trend_limit
        )

    return (
        _dashboard(
            request
        )
        .trends(
            limit=limit
        )
    )
