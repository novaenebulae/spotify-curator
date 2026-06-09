from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.audio.paths import audio_segments_root, segment_absolute_path
from app.audio.pipeline.consumers import segment_cleanup_allowed
from app.audio.provider import CleanupResult
from app.database.engine import get_engine
from app.database.repositories.track_segments import TrackSegmentsRepository
from app.settings.config import settings


class AudioCleanupService:
    def __init__(self, *, segments_repo: TrackSegmentsRepository | None = None) -> None:
        self._segments = segments_repo or TrackSegmentsRepository()

    def cleanup_files(
        self,
        *,
        job_id: str | None = None,
        track_id: int | None = None,
        dry_run: bool = False,
        older_than_hours: int = 0,
        include_failed: bool = False,
    ) -> CleanupResult:
        result = CleanupResult()
        cutoff = datetime.now(tz=UTC).replace(tzinfo=None) - timedelta(hours=older_than_hours)
        root = audio_segments_root()
        if not root.exists():
            return result

        engine = get_engine()
        if track_id is not None:
            with Session(engine) as session:
                segments = self._segments.list_for_track(
                    session, track_id, include_deleted=include_failed
                )
                self._cleanup_segment_list(
                    session,
                    segments,
                    result=result,
                    job_id=job_id,
                    cutoff=cutoff,
                    include_failed=include_failed,
                    dry_run=dry_run,
                )
                if not dry_run:
                    session.commit()
        else:
            with Session(engine) as session:
                segments = []
                for track_dir in root.iterdir():
                    if not track_dir.is_dir():
                        continue
                    try:
                        tid = int(track_dir.name)
                    except ValueError:
                        continue
                    segments.extend(
                        self._segments.list_for_track(
                            session, tid, include_deleted=include_failed
                        )
                    )
                self._cleanup_segment_list(
                    session,
                    segments,
                    result=result,
                    job_id=job_id,
                    cutoff=cutoff,
                    include_failed=include_failed,
                    dry_run=dry_run,
                )
                if not dry_run:
                    session.commit()

        if not dry_run:
            self._prune_empty_dirs(root)
        return result

    def _cleanup_segment_list(
        self,
        session: Session,
        segments: list,
        *,
        result: CleanupResult,
        job_id: str | None,
        cutoff: datetime,
        include_failed: bool,
        dry_run: bool,
    ) -> None:
        seen_paths: set[Path] = set()
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        for seg in segments:
            if job_id and seg.temporary_path and job_id not in seg.temporary_path:
                continue
            if seg.created_at and seg.created_at > cutoff:
                continue
            if seg.deleted_at is not None and not include_failed:
                continue
            if not seg.temporary_path:
                continue
            if settings.audio_cleanup_wait_for_all_consumers and seg.id is not None:
                if not segment_cleanup_allowed(session, segment_id=seg.id):
                    continue
            path = segment_absolute_path(seg.temporary_path)
            if path in seen_paths:
                continue
            seen_paths.add(path)
            result.matched_files += 1
            if dry_run:
                continue
            try:
                if path.is_file():
                    size = path.stat().st_size
                    path.unlink(missing_ok=True)
                    result.deleted_files += 1
                    result.freed_bytes += size
                self._segments.mark_deleted(session, seg.id, deleted_at=now)
                self._segments.update_fields(session, seg.id, temporary_path=None)
            except OSError as e:
                result.errors.append(str(e))

    def cleanup_orphan_files(self, *, dry_run: bool = False) -> CleanupResult:
        result = CleanupResult()
        root = audio_segments_root()
        if not root.exists():
            return result
        engine = get_engine()
        with Session(engine) as session:
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                rel = path.relative_to(Path(settings.cache_dir)).as_posix()
                known = False
                for track_dir in root.iterdir():
                    if not track_dir.is_dir():
                        continue
                    try:
                        tid = int(track_dir.name)
                    except ValueError:
                        continue
                    for seg in self._segments.list_for_track(session, tid, include_deleted=True):
                        if seg.temporary_path == rel:
                            known = True
                            break
                    if known:
                        break
                if known:
                    continue
                result.matched_files += 1
                if dry_run:
                    continue
                try:
                    size = path.stat().st_size
                    path.unlink(missing_ok=True)
                    result.deleted_files += 1
                    result.freed_bytes += size
                except OSError as e:
                    result.errors.append(str(e))
        if not dry_run:
            self._prune_empty_dirs(root)
        return result

    def delete_segment_file(self, relative_path: str, *, dry_run: bool = False) -> bool:
        path = segment_absolute_path(relative_path)
        if not path.is_file():
            return False
        if dry_run:
            return True
        path.unlink(missing_ok=True)
        return True

    def _prune_empty_dirs(self, root: Path) -> None:
        for dirpath, _dirnames, _filenames in os.walk(root, topdown=False):
            p = Path(dirpath)
            if p == root:
                continue
            if not any(p.iterdir()):
                p.rmdir()
