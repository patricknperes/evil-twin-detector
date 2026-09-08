from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status

from .history import HistoryNotFoundError
from .schemas import (
    HistoryDetectionDetailResponse,
    HistoryDetectionListResponse,
    HistoryModelVersionListResponse,
    HistoryModelVersionResponse,
    HistoryObservationListResponse,
    HistoryScanDetailResponse,
    HistoryScanListResponse,
)


router = APIRouter(prefix="/history", tags=["history"])


def _service(request: Request):
    return request.app.state.history_service


def _settings(request: Request):
    return (
        request.app.state
        .settings_service
        .get_values()
    )


@router.get("/scans", response_model=HistoryScanListResponse)
def list_scans(
    request: Request,
    limit: int | None = Query(default=None, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    if limit is None:
        limit = _settings(
            request
        ).history_page_size

    return _service(
        request
    ).list_scans(
        limit=limit,
        offset=offset,
    )


@router.get("/scans/{scan_id}", response_model=HistoryScanDetailResponse)
def scan_detail(scan_id: str, request: Request):
    try:
        return _service(request).get_scan(scan_id)
    except HistoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "history_scan_not_found", "message": str(exc)},
        ) from exc


@router.get(
    "/scans/{scan_id}/observations",
    response_model=HistoryObservationListResponse,
)
def scan_observations(
    scan_id: str,
    request: Request,
    limit: int | None = Query(default=None, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    try:
        if limit is None:
            limit = _settings(
                request
            ).history_observation_page_size

        return _service(
            request
        ).list_scan_observations(
            scan_id,
            limit=limit,
            offset=offset,
        )
    except HistoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "history_scan_not_found", "message": str(exc)},
        ) from exc


@router.get("/detections", response_model=HistoryDetectionListResponse)
def list_detections(
    request: Request,
    limit: int | None = Query(default=None, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    is_anomaly: bool | None = Query(default=None),
    suspicion_level: str | None = Query(default=None, max_length=32),
    model_version_id: int | None = Query(default=None, ge=1),
):
    if limit is None:
        limit = _settings(
            request
        ).history_page_size

    return _service(request).list_detections(
        limit=limit,
        offset=offset,
        is_anomaly=is_anomaly,
        suspicion_level=suspicion_level,
        model_version_id=model_version_id,
    )


@router.get(
    "/detections/{detection_id}",
    response_model=HistoryDetectionDetailResponse,
)
def detection_detail(detection_id: int, request: Request):
    try:
        return _service(request).get_detection(detection_id)
    except HistoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "history_detection_not_found", "message": str(exc)},
        ) from exc


@router.get("/models", response_model=HistoryModelVersionListResponse)
def list_models(
    request: Request,
    limit: int | None = Query(default=None, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    if limit is None:
        limit = _settings(
            request
        ).history_page_size

    return _service(
        request
    ).list_models(
        limit=limit,
        offset=offset,
    )


@router.get(
    "/models/{model_version_id}",
    response_model=HistoryModelVersionResponse,
)
def model_detail(model_version_id: int, request: Request):
    try:
        return _service(request).get_model(model_version_id)
    except HistoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "history_model_not_found", "message": str(exc)},
        ) from exc
