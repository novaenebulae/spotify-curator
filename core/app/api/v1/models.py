from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.models_registry import ModelManager, ModelManagerError
from app.observability.errors import ApiError
from app.settings.config import settings

router = APIRouter(prefix="/models")


class ModelStatusItem(BaseModel):
    model_key: str
    display_name: str
    task: str
    status: str
    required_for: list[str] = Field(default_factory=list)
    license: str | None = None
    local_weights_path: str | None = None
    local_metadata_path: str | None = None
    sha256: str | None = None
    expected_sha256: str | None = None
    size_bytes: int | None = None


class ModelProfileItem(BaseModel):
    name: str
    status: str
    available_count: int = 0
    missing_count: int = 0
    description: str = ""


class ModelStatusSummaryResponse(BaseModel):
    total: int = 0
    available: int = 0
    missing: int = 0
    invalid_hash: int = 0
    disabled: int = 0
    real_inference_ready: bool = False
    default_profile: str = ""


class ModelsStatusResponse(BaseModel):
    summary: ModelStatusSummaryResponse
    profiles: list[ModelProfileItem] = Field(default_factory=list)
    models: list[ModelStatusItem] = Field(default_factory=list)
    models_dir: str = Field(default_factory=lambda: settings.essentia_models_dir)


class DownloadModelRequest(BaseModel):
    model_key: str
    accept_license: bool = False
    force: bool = False


class DownloadProfileRequest(BaseModel):
    profile: str
    accept_license: bool = False
    force: bool = False


class VerifyModelRequest(BaseModel):
    model_key: str


def _as_api_error(exc: ModelManagerError) -> ApiError:
    return ApiError(
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
    )


@router.get("/status", response_model=ModelsStatusResponse)
def get_models_status() -> ModelsStatusResponse:
    try:
        status = ModelManager().get_status()
    except ModelManagerError as exc:
        raise _as_api_error(exc) from exc
    return ModelsStatusResponse(
        summary=ModelStatusSummaryResponse(**status["summary"]),
        profiles=[ModelProfileItem(**p) for p in status["profiles"]],
        models=[ModelStatusItem(**m) for m in status["models"]],
        models_dir=settings.essentia_models_dir,
    )


@router.post("/download")
def download_model(body: DownloadModelRequest) -> dict[str, Any]:
    try:
        return ModelManager().download_model(
            body.model_key, accept_license=body.accept_license, force=body.force
        )
    except ModelManagerError as exc:
        raise _as_api_error(exc) from exc


@router.post("/download-profile")
def download_profile(body: DownloadProfileRequest) -> dict[str, Any]:
    try:
        return ModelManager().download_profile(
            body.profile, accept_license=body.accept_license, force=body.force
        )
    except ModelManagerError as exc:
        raise _as_api_error(exc) from exc


@router.post("/verify")
def verify_model(body: VerifyModelRequest) -> dict[str, Any]:
    try:
        return ModelManager().verify_model(body.model_key)
    except ModelManagerError as exc:
        raise _as_api_error(exc) from exc
