from fastapi import APIRouter

from app.api.v1.audio import router as audio_router
from app.api.v1.diagnostics import router as diagnostics_router
from app.api.v1.exports import router as exports_router
from app.api.v1.features import router as features_router
from app.api.v1.health import router as health_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.library import router as library_router
from app.api.v1.models import router as models_router
from app.api.v1.previews import router as previews_router
from app.api.v1.runtime import router as runtime_router
from app.api.v1.snapshots import router as snapshots_router
from app.api.v1.spotify_auth import router as spotify_auth_router
from app.api.v1.spotify_import import router as spotify_import_router
from app.api.v1.generated_playlists import router as generated_playlists_router
from app.api.v1.playlist_rules import router as playlist_rules_router
from app.api.v1.sync import router as sync_router
from app.api.v1.tracks import router as tracks_router
from app.api.v1.workers import router as workers_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(runtime_router, tags=["runtime"])
router.include_router(diagnostics_router, tags=["diagnostics"])
router.include_router(jobs_router, tags=["jobs"])
router.include_router(snapshots_router, tags=["snapshots"])
router.include_router(library_router, tags=["library"])
router.include_router(spotify_auth_router, tags=["spotify_auth"])
router.include_router(spotify_import_router, tags=["spotify_import"])
router.include_router(exports_router, tags=["exports"])
router.include_router(features_router, tags=["features"])
router.include_router(models_router, tags=["models"])
router.include_router(audio_router, tags=["audio"])
router.include_router(previews_router, tags=["previews"])
router.include_router(workers_router, tags=["workers"])
router.include_router(playlist_rules_router)
router.include_router(generated_playlists_router)
router.include_router(sync_router)
router.include_router(tracks_router, tags=["tracks"])
