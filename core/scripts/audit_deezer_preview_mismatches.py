#!/usr/bin/env python3
"""Audit Deezer preview matches against ISRC-canonical tracks and optionally remediate.

From repo root:

  uv run --project core python core/scripts/audit_deezer_preview_mismatches.py --output /tmp/deezer_audit.json

Remediation:

  uv run --project core python core/scripts/audit_deezer_preview_mismatches.py \\
    --output /tmp/deezer_audit.json --reresolve --reanalyze
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audio.advanced_analysis_job_service import AdvancedAnalysisJobService
from app.audio.pipeline.constants import JOB_TYPE_AUDIO_ANALYSIS_PIPELINE
from app.database.engine import get_engine
from app.database.models_jobs import Job
from app.previews.deezer_audit_service import DeezerAuditService, write_audit_csv
from app.previews.deezer_audit_verdicts import REMEDIATION_VERDICTS

_PIPELINE_ACTIVE = frozenset({"queued", "running"})
_PIPELINE_POLL_SECONDS = 15


def _wait_for_pipeline_slot(engine, *, timeout_seconds: int = 86400) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with Session(engine) as session:
            row = session.execute(
                select(Job.id).where(
                    Job.job_type == JOB_TYPE_AUDIO_ANALYSIS_PIPELINE,
                    Job.status.in_(tuple(_PIPELINE_ACTIVE)),
                )
            ).first()
            if row is None:
                return
            job_id = row[0]
        print(f"reanalyze_waiting job_id={job_id}", flush=True)
        time.sleep(_PIPELINE_POLL_SECONDS)
    raise TimeoutError("Timed out waiting for audio_analysis_pipeline slot")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="JSON report output path")
    parser.add_argument("--csv", default=None, help="Optional CSV report path")
    parser.add_argument("--limit", type=int, default=None, help="Max tracks to audit")
    parser.add_argument(
        "--reresolve",
        action="store_true",
        help="Re-resolve previews for mismatch / low-confidence fuzzy tracks",
    )
    parser.add_argument(
        "--reanalyze",
        action="store_true",
        help="Queue audio_analysis_pipeline for remediated track_ids (force_refresh)",
    )
    parser.add_argument(
        "--reanalyze-chunk-size",
        type=int,
        default=100,
        help="Tracks per pipeline job when --reanalyze is set",
    )
    args = parser.parse_args()

    svc = DeezerAuditService()
    engine = get_engine()

    with Session(engine) as session:
        track_ids = svc.list_track_ids_to_audit(session, limit=args.limit)
        report = svc.audit_tracks(session, track_ids)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    print(f"audited={len(report.rows)} output={output_path}")
    print(f"summary={json.dumps(report.summary)}")

    if args.csv:
        write_audit_csv(args.csv, report)
        print(f"csv={args.csv}")

    remediation_ids = [
        row.track_id for row in report.rows if row.verdict in REMEDIATION_VERDICTS
    ]
    reresolve_results: list[dict] = []

    if args.reresolve and remediation_ids:
        with Session(engine) as session:
            reresolve_results = svc.reresolve_tracks(session, remediation_ids)
        print(f"reresolved={len(reresolve_results)}")

        with Session(engine) as session:
            report = svc.audit_tracks(session, remediation_ids)
        print(f"post_reresolve_summary={json.dumps(report.summary)}")

    if args.reanalyze:
        reanalyze_ids = remediation_ids
        if args.reresolve:
            reanalyze_ids = [
                row.track_id for row in report.rows if row.verdict in REMEDIATION_VERDICTS
            ]
            reanalyze_ids = list(dict.fromkeys(remediation_ids + reanalyze_ids))
        if not reanalyze_ids:
            print("reanalyze=skipped no track_ids")
            return 0

        analysis = AdvancedAnalysisJobService()
        job_ids: list[str] = []
        for i in range(0, len(reanalyze_ids), args.reanalyze_chunk_size):
            _wait_for_pipeline_slot(engine)
            chunk = reanalyze_ids[i : i + args.reanalyze_chunk_size]
            job_id = analysis.start_advanced_analysis_job(
                track_ids=chunk,
                only_missing=False,
                force_refresh=True,
            )
            job_ids.append(job_id)
            print(f"reanalyze_job={job_id} tracks={len(chunk)}")
        print(f"reanalyze_jobs={len(job_ids)} total_tracks={len(reanalyze_ids)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
