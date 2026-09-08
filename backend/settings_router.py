from __future__ import annotations

from fastapi import (
    APIRouter,
    Request,
)

from .schemas import (
    ApplicationSettingsResponse,
    ApplicationSettingsUpdate,
)


router = APIRouter(
    prefix="/settings",
    tags=[
        "settings"
    ],
)


def _service(
    request: Request,
):
    return (
        request.app.state
        .settings_service
    )


@router.get(
    "",
    response_model=(
        ApplicationSettingsResponse
    ),
)
def get_settings(
    request: Request,
) -> ApplicationSettingsResponse:
    return (
        _service(
            request
        )
        .get_response()
    )


@router.patch(
    "",
    response_model=(
        ApplicationSettingsResponse
    ),
)
def update_settings(
    patch:
        ApplicationSettingsUpdate,
    request: Request,
) -> ApplicationSettingsResponse:
    return (
        _service(
            request
        )
        .update(
            patch
        )
    )


@router.post(
    "/reset",
    response_model=(
        ApplicationSettingsResponse
    ),
)
def reset_settings(
    request: Request,
) -> ApplicationSettingsResponse:
    return (
        _service(
            request
        )
        .reset()
    )
