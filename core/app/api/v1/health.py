from fastapi import APIRouter

from app.settings.config import settings

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "spotify-curator-core",
        "version": settings.app_version,
    }
