#!/usr/bin/env python3
"""Sample pipeline stage success counts and compute per-minute rates."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import UTC, datetime

from sqlalchemy import create_engine, text

JOB_ID = "cdf42ab6d7e641a0bc99795a53556255"
STAGES = ("segment_download", "essentia_lowlevel", "essentia_tensorflow")


def gpu_snapshot() -> str:
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        parts = [p.strip() for p in out.split(",")]
        if len(parts) >= 3:
            return f"VRAM {parts[0]}/{parts[1]} MiB, GPU util {parts[2]}%"
    except Exception:
        pass
    return "GPU n/a"


def counts(job_id: str) -> dict[str, int]:
    url = os.environ.get("DATABASE_URL", "sqlite:////data/spotify_curator.sqlite")
    engine = create_engine(url)
    with engine.connect() as conn:
        out: dict[str, int] = {}
        for stage in STAGES:
            row = conn.execute(
                text(
                    "SELECT COUNT(*) FROM job_items "
                    "WHERE job_id=:j AND stage_name=:s AND status='success'"
                ),
                {"j": job_id, "s": stage},
            ).scalar()
            out[stage] = int(row or 0)
        pending_tf = conn.execute(
            text(
                "SELECT COUNT(*) FROM job_items tf "
                "JOIN job_items ll ON ll.job_id=tf.job_id AND ll.track_id=tf.track_id "
                "AND ll.stage_name='essentia_lowlevel' AND ll.status='success' "
                "WHERE tf.job_id=:j AND tf.stage_name='essentia_tensorflow' "
                "AND tf.status='pending'"
            ),
            {"j": job_id},
        ).scalar()
        out["tf_ready_pending"] = int(pending_tf or 0)
        return out


def short(stage: str) -> str:
    return {
        "segment_download": "dl",
        "essentia_lowlevel": "ll",
        "essentia_tensorflow": "tf",
    }[stage]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", default=JOB_ID)
    parser.add_argument("--duration-sec", type=int, default=300)
    parser.add_argument("--interval-sec", type=int, default=30)
    parser.add_argument("--label", default="run")
    args = parser.parse_args()

    samples: list[tuple[float, dict[str, int]]] = []
    t0 = time.monotonic()
    print(f"=== {args.label} === job={args.job_id} duration={args.duration_sec}s interval={args.interval_sec}s")
    print(f"start_utc={datetime.now(UTC).isoformat()} {gpu_snapshot()}")

    while True:
        elapsed = time.monotonic() - t0
        if elapsed > args.duration_sec:
            break
        c = counts(args.job_id)
        samples.append((elapsed, c))
        print(
            f"t={elapsed:5.0f}s  dl={c['segment_download']:4d}  ll={c['essentia_lowlevel']:4d}  "
            f"tf={c['essentia_tensorflow']:4d}  tf_ready={c['tf_ready_pending']:4d}  "
            f"{gpu_snapshot()}"
        )
        if elapsed + args.interval_sec > args.duration_sec:
            break
        time.sleep(args.interval_sec)

    if len(samples) < 2:
        print("Not enough samples")
        return 1

    first_t, first_c = samples[0]
    last_t, last_c = samples[-1]
    dt_min = max((last_t - first_t) / 60.0, 1e-6)
    print(f"\n--- rates ({args.label}, window {last_t - first_t:.0f}s) ---")
    for stage in STAGES:
        delta = last_c[stage] - first_c[stage]
        rate = delta / dt_min
        print(f"  {short(stage):>2}: +{delta:4d}  => {rate:5.1f}/min")
    print(f"  tf backlog (ready pending): {last_c['tf_ready_pending']}")
    print(f"end_utc={datetime.now(UTC).isoformat()} {gpu_snapshot()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
