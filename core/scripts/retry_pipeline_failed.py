#!/usr/bin/env python3
"""Retry failed pipeline stage items for a running audio_analysis_pipeline job."""

from __future__ import annotations

import argparse
import sys

from app.audio.pipeline.constants import (
    STAGE_ESSENTIA_LOWLEVEL,
    STAGE_ESSENTIA_TENSORFLOW,
    STAGE_SEGMENT_DOWNLOAD,
)
from app.audio.pipeline.orchestrator import AnalysisPipelineOrchestrator


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_id", help="audio_analysis_pipeline job id")
    parser.add_argument(
        "--stages",
        nargs="*",
        default=[
            STAGE_SEGMENT_DOWNLOAD,
            STAGE_ESSENTIA_LOWLEVEL,
            STAGE_ESSENTIA_TENSORFLOW,
        ],
        help="Pipeline stage names to retry (default: download, lowlevel, tensorflow)",
    )
    args = parser.parse_args()

    orch = AnalysisPipelineOrchestrator()
    count = orch.retry_failed_items_for_job(
        args.job_id,
        stage_names=tuple(args.stages),
        reset_attempt_count=True,
    )
    print(f"retried={count} job_id={args.job_id} stages={args.stages}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
