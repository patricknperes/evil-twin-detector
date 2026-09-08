from __future__ import annotations

from fastapi import APIRouter, Request

from .schemas import DiagnosticsSupportBundleResponse

router = APIRouter(prefix="/diagnostics", tags=["system"])


@router.get(
    "/support-bundle",
    response_model=DiagnosticsSupportBundleResponse,
)
def support_bundle(request: Request) -> DiagnosticsSupportBundleResponse:
    return request.app.state.diagnostics_service.create_support_bundle()
