from __future__ import annotations

JOB_TYPE_AUDIO_ANALYSIS_PIPELINE = "audio_analysis_pipeline"
ITEM_TYPE_ANALYSIS_PIPELINE_STAGE = "analysis_pipeline_stage"

STAGE_SEGMENT_DOWNLOAD = "segment_download"
STAGE_ESSENTIA_LOWLEVEL = "essentia_lowlevel"
STAGE_ESSENTIA_TENSORFLOW_EMBEDDINGS = "essentia_tensorflow_embeddings"
STAGE_ESSENTIA_TENSORFLOW_CLASSIFIERS = "essentia_tensorflow_classifiers"
STAGE_FEATURE_AGGREGATION = "feature_aggregation"
STAGE_AUDIO_CLEANUP = "audio_cleanup"

ALL_PIPELINE_STAGES = (
    STAGE_SEGMENT_DOWNLOAD,
    STAGE_ESSENTIA_LOWLEVEL,
    STAGE_ESSENTIA_TENSORFLOW_EMBEDDINGS,
    STAGE_ESSENTIA_TENSORFLOW_CLASSIFIERS,
    STAGE_FEATURE_AGGREGATION,
    STAGE_AUDIO_CLEANUP,
)

STAGE_STATUSES = frozenset(
    {
        "pending",
        "running",
        "success",
        "failed",
        "skipped",
        "blocked",
        "cancelled",
        "rate_limited",
    }
)

TERMINAL_FOR_DEPENDENCY = frozenset({"success", "skipped", "failed"})
BLOCKED_REASON_DEPENDENCY_PENDING = "dependency_pending"

PIPELINE_MODE_STREAMING = "streaming"
PIPELINE_MODE_LEGACY = "legacy"

SEGMENT_CONSUMER_STAGES = frozenset(
    {
        STAGE_ESSENTIA_LOWLEVEL,
        STAGE_ESSENTIA_TENSORFLOW_EMBEDDINGS,
        STAGE_ESSENTIA_TENSORFLOW_CLASSIFIERS,
    }
)

ACTIVE_SEGMENT_CONSUMER_STATUSES = frozenset(
    {"pending", "running", "rate_limited", "blocked"}
)
