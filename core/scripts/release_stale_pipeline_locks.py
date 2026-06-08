#!/usr/bin/env python3
"""Release stale pipeline stage item locks (e.g. after worker crashes)."""

from __future__ import annotations

import sys

from app.jobs.items.service import JobItemService


def main() -> int:
    items = JobItemService()
    stale = items.release_stale_pipeline_stage_locks()
    print(f"released_stale_locks={stale}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
