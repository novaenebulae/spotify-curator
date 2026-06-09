#!/usr/bin/env python3
"""Launch one pipeline job for Deezer-failed tracks (YouTube fallback at download workers)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from app.audio.advanced_analysis_job_service import AdvancedAnalysisJobService


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="/app/data/local_analysis_diagnostic.json",
        help="Diagnostic JSON with track_ids",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Re-analyze all candidate tracks (ignore existing TF/low-level)",
    )
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    ids = list(data.get("track_ids") or [])
    ids.extend(data.get("deezer_ok_missing_tf") or [])
    ids = list(dict.fromkeys(ids))

    print(f"candidates={len(ids)}", flush=True)
    if args.dry_run:
        return 0

    svc = AdvancedAnalysisJobService()
    job_id = svc.start_advanced_analysis_job(
        track_ids=ids,
        strategy="hybrid_deezer_youtube_representative",
        only_missing=not args.force_refresh,
        include_tensorflow=True,
        include_lowlevel=True,
        force_refresh=args.force_refresh,
        retry_failed=False,
    )
    print(f"job_id={job_id}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
