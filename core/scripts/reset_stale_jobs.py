#!/usr/bin/env python3
"""Reset stale pipeline job_item locks back to pending."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_CORE_ROOT = Path(__file__).resolve().parents[1]
if str(_CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CORE_ROOT))

from sqlalchemy import and_, or_, select, update  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.database.engine import get_engine  # noqa: E402
from app.database.models_job_items import JobItem  # noqa: E402
from app.jobs.items.constants import PIPELINE_STAGES_BY_WORKER, WORKER_TYPE_ESSENTIA_TENSORFLOW  # noqa: E402
from app.jobs.items.service import JobItemService  # noqa: E402
from app.settings.config import settings  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reset stale running pipeline job items")
    parser.add_argument(
        "--stage",
        help="Limit to a single pipeline stage (e.g. essentia_tensorflow_embeddings)",
    )
    parser.add_argument(
        "--worker-type",
        default=WORKER_TYPE_ESSENTIA_TENSORFLOW,
        help="Worker type for lock-timeout scope (default: essentia_tensorflow)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print affected rows without updating the database",
    )
    return parser.parse_args()


def _stage_filter(stage: str | None):
    if not stage:
        return None
    return JobItem.stage_name == stage


def main() -> int:
    args = _parse_args()
    print(f"database_url={settings.database_url}")
    if args.dry_run:
        print("DRY RUN — no changes will be written")
    print("Tip: back up SQLite before resetting production data.")

    service = JobItemService()
    engine = get_engine()

    with Session(engine) as session:
        stmt = select(JobItem).where(JobItem.status == "running")
        stage_clause = _stage_filter(args.stage)
        if stage_clause is not None:
            stmt = stmt.where(stage_clause)
        elif args.worker_type in PIPELINE_STAGES_BY_WORKER:
            stages = PIPELINE_STAGES_BY_WORKER[args.worker_type]
            stmt = stmt.where(JobItem.stage_name.in_(stages))

        candidates = session.scalars(stmt).all()
        print(f"candidate running items: {len(candidates)}")
        for item in candidates:
            print(
                f"  {item.id} stage={item.stage_name} locked_by={item.locked_by} "
                f"locked_at={item.locked_at}"
            )

    if args.dry_run:
        lock_timeout = service.lock_timeout_for_worker(args.worker_type)
        print(f"would also release stale locks (timeout={lock_timeout}s) via JobItemService")
        return 0

    released = service.release_stale_locks(worker_type=args.worker_type)
    print(f"released stale locks: {released}")

    if args.stage:
        with Session(engine) as session:
            result = session.execute(
                update(JobItem)
                .where(
                    JobItem.status == "running",
                    JobItem.stage_name == args.stage,
                    or_(
                        JobItem.locked_at.is_(None),
                        and_(
                            JobItem.locked_by.is_not(None),
                            JobItem.locked_at.is_not(None),
                        ),
                    ),
                )
                .values(status="pending", locked_by=None, locked_at=None)
            )
            session.commit()
            forced = int(result.rowcount or 0)
        print(f"forced reset for stage {args.stage!r}: {forced}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
