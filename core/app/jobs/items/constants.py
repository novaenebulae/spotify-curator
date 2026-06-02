from __future__ import annotations

JOB_TYPE_AUDIO_DOWNLOAD = "audio_download"
JOB_TYPE_ESSENTIA_LOWLEVEL = "essentia_lowlevel_analysis"
JOB_TYPE_PREVIEW_RESOLVE = "preview_resolve"

ITEM_TYPE_AUDIO_DOWNLOAD_TRACK = "audio_download_track"
ITEM_TYPE_ESSENTIA_LOWLEVEL_TRACK = "essentia_lowlevel_track"
ITEM_TYPE_PREVIEW_RESOLVE_TRACK = "preview_resolve_track"

WORKER_TYPE_AUDIO_DOWNLOADER = "audio_downloader"
WORKER_TYPE_ESSENTIA_LOWLEVEL = "essentia_lowlevel"
WORKER_TYPE_PREVIEW_RESOLVER = "preview_resolver"

WORKER_ITEM_TYPES: dict[str, tuple[str, ...]] = {
    WORKER_TYPE_AUDIO_DOWNLOADER: (ITEM_TYPE_AUDIO_DOWNLOAD_TRACK,),
    WORKER_TYPE_ESSENTIA_LOWLEVEL: (ITEM_TYPE_ESSENTIA_LOWLEVEL_TRACK,),
    WORKER_TYPE_PREVIEW_RESOLVER: (ITEM_TYPE_PREVIEW_RESOLVE_TRACK,),
}

TERMINAL_ITEM_STATUSES = frozenset(
    {"success", "failed", "cancelled", "skipped", "rate_limited"}
)

# Jobs executed by Docker workers (not in-process JobService threads).
WORKER_MANAGED_JOB_TYPES = frozenset(
    {
        JOB_TYPE_PREVIEW_RESOLVE,
        JOB_TYPE_AUDIO_DOWNLOAD,
        JOB_TYPE_ESSENTIA_LOWLEVEL,
    }
)
