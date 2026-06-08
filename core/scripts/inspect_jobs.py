#!/usr/bin/env python3
"""Inspect pipeline job items — counts, recent TensorFlow items, stale locks."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

_CORE_ROOT = Path(__file__).resolve().parents[1]
if str(_CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CORE_ROOT))

from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.audio.pipeline.constants import (  # noqa: E402
    STAGE_ESSENTIA_TENSORFLOW,
    STAGE_ESSENTIA_TENSORFLOW_CLASSIFIERS,
    STAGE_ESSENTIA_TENSORFLOW_EMBEDDINGS,
)
from app.database.engine import get_engine  # noqa: E402
from app.database.models_job_items import JobItem  # noqa: E402
from app.settings.config import settings  # noqa: E402

_TF_STAGES = (
    STAGE_ESSENTIA_TENSORFLOW,
    STAGE_ESSENTIA_TENSORFLOW_EMBEDDINGS,
    STAGE_ESSENTIA_TENSORFLOW_CLASSIFIERS,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect job_items for pipeline diagnostics")
    parser.add_argument("--limit", type=int, default=20, help="Recent TF items to list")
    parser.add_argument(
        "--stale-minutes",
        type=int,
        default=30,
        help="Flag running items locked longer than this",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    engine = get_engine()
    now = datetime.now(tz=UTC).replace(tzinfo=None)
    stale_before = now - timedelta(minutes=args.stale_minutes)

    print(f"database_url={settings.database_url}")
    print()

    with Session(engine) as session:
        rows = session.execute(
            select(JobItem.stage_name, JobItem.status, func.count())
            .where(JobItem.stage_name.is_not(None))
            .group_by(JobItem.stage_name, JobItem.status)
            .order_by(JobItem.stage_name, JobItem.status)
        ).all()

        by_stage: dict[str, dict[str, int]] = defaultdict(dict)
        for stage_name, status, count in rows:
            by_stage[str(stage_name)][str(status)] = int(count)

        print("=== counts by stage / status ===")
        for stage in sorted(by_stage):
            print(f"  {stage}: {by_stage[stage]}")

        stale = session.scalars(
            select(JobItem)
            .where(
                JobItem.status == "running",
                JobItem.locked_at.is_not(None),
                JobItem.locked_at < stale_before,
            )
            .order_by(JobItem.locked_at)
        ).all()

        print()
        print(f"=== stale running locks (>{args.stale_minutes}m) ===")
        if not stale:
            print("  (none)")
        for item in stale:
            print(
                f"  {item.id} stage={item.stage_name} locked_by={item.locked_by} "
                f"locked_at={item.locked_at} job={item.job_id}"
            )

        recent = session.scalars(
            select(JobItem)
            .where(JobItem.stage_name.in_(_TF_STAGES))
            .order_by(JobItem.created_at.desc())
            .limit(args.limit)
        ).all()

        print()
        print(f"=== last {args.limit} tensorflow pipeline items ===")
        for item in recent:
            print(
                json.dumps(
                    {
                        "id": item.id,
                        "job_id": item.job_id,
                        "stage_name": item.stage_name,
                        "status": item.status,
                        "pipeline_version": item.pipeline_version,
                        "locked_by": item.locked_by,
                        "locked_at": item.locked_at.isoformat() if item.locked_at else None,
                        "error_code": item.error_code,
                        "last_error": (item.error_message or "")[:200] or None,
                    },
                    default=str,
                )
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
