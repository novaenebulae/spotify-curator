#!/usr/bin/env python3
"""Benchmark advanced audio pipeline (Lambda GPU or local API)."""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

_CORE_ROOT = Path(__file__).resolve().parents[1]
if str(_CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CORE_ROOT))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark advanced analysis pipeline")
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--profile", default="phase6-recommended")
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument("--timeout-seconds", type=float, default=7200.0)
    return parser.parse_args()


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, int(len(ordered) * 0.95) - 1)
    return ordered[idx]


def main() -> int:
    args = _parse_args()
    base = args.base_url.rstrip("/")
    api = f"{base}/api/v1"

    payload = {
        "only_missing": True,
        "include_lowlevel": True,
        "include_tensorflow": True,
        "limit": args.limit,
        "model_profile": args.profile,
        "require_real_tensorflow": False,
    }

    started = time.perf_counter()
    with httpx.Client(timeout=60.0) as client:
        res = client.post(f"{api}/audio/analysis/advanced", json=payload)
        res.raise_for_status()
        job_id = res.json()["job_id"]
        print(f"Started job {job_id} (limit={args.limit}, profile={args.profile})")

        deadline = time.perf_counter() + args.timeout_seconds
        job_body: dict | None = None
        while time.perf_counter() < deadline:
            job_res = client.get(f"{api}/jobs/{job_id}")
            job_res.raise_for_status()
            job_body = job_res.json()
            status = job_body.get("status")
            if status in {"success", "failed", "partial", "cancelled"}:
                break
            time.sleep(args.poll_seconds)

    if job_body is None:
        print("Job polling failed", file=sys.stderr)
        return 1

    total_s = time.perf_counter() - started
    items_res = httpx.get(f"{api}/jobs/{job_id}/items", timeout=60.0)
    items_res.raise_for_status()
    items = items_res.json().get("items") or []

    tf_durations_ms: list[float] = []
    segment_count = 0
    track_ids: set[int] = set()
    for item in items:
        if item.get("stage_name") != "essentia_tensorflow":
            continue
        segment_count += 1
        if item.get("track_id") is not None:
            track_ids.add(int(item["track_id"]))
        started_at = item.get("started_at")
        finished_at = item.get("finished_at")
        if started_at and finished_at:
            try:
                s = datetime.fromisoformat(str(started_at))
                f = datetime.fromisoformat(str(finished_at))
                tf_durations_ms.append((f - s).total_seconds() * 1000)
            except ValueError:
                pass
        result = item.get("result_json")
        if isinstance(result, dict):
            timing = result.get("timing_ms")
            if isinstance(timing, dict) and timing.get("total_tensorflow_stage_ms"):
                tf_durations_ms.append(float(timing["total_tensorflow_stage_ms"]))

    workers_res = httpx.get(f"{api}/workers?worker_type=essentia_tensorflow", timeout=30.0)
    tf_workers = 0
    gpu_flag = "unknown"
    if workers_res.is_success:
        workers = workers_res.json().get("workers") or []
        tf_workers = len(workers)
        for w in workers:
            meta = w.get("metadata") or {}
            boot = meta.get("boot_metrics") or {}
            if boot.get("gpu_available") is True:
                gpu_flag = "true"
                break
            if boot.get("gpu_available") is False:
                gpu_flag = "false"

    runtime_res = httpx.get(f"{api}/runtime/config", timeout=30.0)
    batch_size = 1
    if runtime_res.is_success:
        batch_size = int(runtime_res.json().get("essentia_tf_batch_size") or 1)

    tracks = len(track_ids) or int(job_body.get("progress_total") or 0)
    minutes = total_s / 60.0 if total_s > 0 else 0.0
    tracks_per_min = tracks / minutes if minutes > 0 else 0.0
    segments_per_min = segment_count / minutes if minutes > 0 else 0.0

    print("\n=== Benchmark summary ===")
    print(f"job_id: {job_id}")
    print(f"status: {job_body.get('status')}")
    print(f"total_duration_s: {total_s:.1f}")
    print(f"tracks: {tracks}")
    print(f"segments_tf: {segment_count}")
    print(f"tracks_per_min: {tracks_per_min:.2f}")
    print(f"segments_per_min: {segments_per_min:.2f}")
    if tf_durations_ms:
        print(f"avg_essentia_tensorflow_ms: {statistics.mean(tf_durations_ms):.1f}")
        print(f"p95_essentia_tensorflow_ms: {_p95(tf_durations_ms):.1f}")
    print(f"tf_workers: {tf_workers}")
    print(f"gpu_available: {gpu_flag}")
    print(f"profile: {args.profile}")
    print(f"batch_size: {batch_size}")

    return 0 if job_body.get("status") in {"success", "partial"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
