#!/usr/bin/env python3
"""Dedicated pipeline ticker worker (aggregation + cleanup), separate from core-api."""

from __future__ import annotations

import logging
import signal
import time

from app.audio.pipeline.ticker import AnalysisPipelineTicker
from app.settings.config import settings

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s [%(name)s] %(message)s",
    )
    running = True

    def _stop(*_args: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    ticker = AnalysisPipelineTicker()
    interval = max(1, settings.analysis_pipeline_tick_interval_seconds)
    logger.info("pipeline-ticker-worker starting interval=%ss", interval)

    while running:
        tick_started = time.monotonic()
        try:
            result = ticker.tick_running_jobs()
            if (
                result.aggregation_ran
                or result.cleanup_ran
                or result.dependencies_unblocked
            ):
                logger.info(
                    "pipeline_tick agg=%d cleanup=%d unblocked=%d jobs=%d",
                    result.aggregation_ran,
                    result.cleanup_ran,
                    result.dependencies_unblocked,
                    result.jobs_ticked,
                )
        except Exception:
            logger.exception("pipeline tick failed")
        if running:
            elapsed = time.monotonic() - tick_started
            time.sleep(max(0.0, interval - elapsed))

    logger.info("pipeline-ticker-worker stopped")


if __name__ == "__main__":
    main()
