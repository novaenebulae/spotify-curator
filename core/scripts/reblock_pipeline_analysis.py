#!/usr/bin/env python3
"""Re-block analysis stages that failed/skipped before segment download completed."""

from __future__ import annotations

import argparse
import sys

from app.audio.pipeline.orchestrator import AnalysisPipelineOrchestrator


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_id", help="audio_analysis_pipeline job id")
    args = parser.parse_args()

    orch = AnalysisPipelineOrchestrator()
    count = orch.reblock_failed_analysis_waiting_for_segment(args.job_id)
    print(f"reblocked={count} job_id={args.job_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
