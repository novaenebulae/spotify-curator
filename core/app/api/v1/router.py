from fastapi import APIRouter

from app.api.v1.diagnostics import router as diagnostics_router
from app.api.v1.exports import router as exports_router
from app.api.v1.health import router as health_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.snapshots import router as snapshots_router
from app.api.v1.spotify_auth import router as spotify_auth_router
from app.api.v1.spotify_import import router as spotify_import_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(diagnostics_router, tags=["diagnostics"])
router.include_router(jobs_router, tags=["jobs"])
router.include_router(snapshots_router, tags=["snapshots"])
router.include_router(spotify_auth_router, tags=["spotify_auth"])
router.include_router(spotify_import_router, tags=["spotify_import"])
router.include_router(exports_router, tags=["exports"])

