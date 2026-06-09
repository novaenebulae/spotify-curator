from __future__ import annotations

import csv
import time
from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audio.track_context import load_track_context
from app.database.models_audio import AudioDownloadJob, TrackSegment
from app.database.models_previews import TrackPreview
from app.database.repositories.audio_download_jobs import AudioDownloadJobsRepository
from app.database.repositories.track_previews import TrackPreviewsRepository
from app.previews.deezer_audit_verdicts import (
    DEEZER_ANALYSIS_DECISIONS,
    VERDICT_NO_SPOTIFY_ISRC,
    analysis_decision_from_json,
    classify_deezer_audit_verdict,
)
from app.previews.deezer_client import DeezerClient
from app.previews.deezer_provider import DeezerPreviewProvider
from app.previews.upsert import PreviewUpsertService


@dataclass(frozen=True)
class DeezerAuditRow:
    track_id: int
    spotify_isrc: str | None
    stored_deezer_id: str | None
    isrc_deezer_id: str | None
    stored_title: str | None
    isrc_title: str | None
    stored_match_strategy: str | None
    stored_match_confidence: float | None
    analysis_decision: str | None
    verdict: str
    details: str | None = None


@dataclass(frozen=True)
class DeezerAuditReport:
    rows: tuple[DeezerAuditRow, ...]
    summary: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "rows": [asdict(r) for r in self.rows],
        }


class DeezerAuditService:
    def __init__(
        self,
        *,
        client: DeezerClient | None = None,
        provider: DeezerPreviewProvider | None = None,
        previews_repo: TrackPreviewsRepository | None = None,
        downloads_repo: AudioDownloadJobsRepository | None = None,
        upsert: PreviewUpsertService | None = None,
        rate_limit_seconds: float = 0.34,
    ) -> None:
        self._client = client or DeezerClient()
        self._provider = provider or DeezerPreviewProvider(client=self._client)
        self._previews = previews_repo or TrackPreviewsRepository()
        self._downloads = downloads_repo or AudioDownloadJobsRepository()
        self._upsert = upsert or PreviewUpsertService(self._previews)
        self._rate_limit_seconds = rate_limit_seconds

    def list_track_ids_to_audit(self, session: Session, *, limit: int | None = None) -> list[int]:
        ids: set[int] = set()

        preview_rows = session.execute(
            select(TrackPreview.track_id).where(
                TrackPreview.provider == "deezer",
                TrackPreview.is_available.is_(True),
                TrackPreview.preview_url.is_not(None),
            )
        ).scalars().all()
        ids.update(int(tid) for tid in preview_rows)

        download_rows = session.execute(select(AudioDownloadJob.track_id, AudioDownloadJob.result_json)).all()
        for track_id, result_json in download_rows:
            decision = analysis_decision_from_json(result_json)
            if decision in DEEZER_ANALYSIS_DECISIONS:
                ids.add(int(track_id))

        segment_rows = session.execute(
            select(TrackSegment.track_id).where(TrackSegment.source == "deezer_preview").distinct()
        ).scalars().all()
        ids.update(int(tid) for tid in segment_rows)

        ordered = sorted(ids)
        if limit is not None:
            ordered = ordered[:limit]
        return ordered

    def audit_tracks(
        self,
        session: Session,
        track_ids: list[int],
    ) -> DeezerAuditReport:
        rows: list[DeezerAuditRow] = []
        for track_id in track_ids:
            rows.append(self._audit_one(session, track_id))
            time.sleep(self._rate_limit_seconds)
        summary: dict[str, int] = {}
        for row in rows:
            summary[row.verdict] = summary.get(row.verdict, 0) + 1
        return DeezerAuditReport(rows=tuple(rows), summary=summary)

    def reresolve_tracks(self, session: Session, track_ids: list[int]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for track_id in track_ids:
            before = self._previews.get_for_track_provider(session, track_id=track_id, provider="deezer")
            ctx = load_track_context(session, track_id)
            candidate = self._provider.resolve_preview(ctx)
            self._upsert.upsert_candidate(session, track_id=track_id, candidate=candidate)
            session.commit()
            results.append(
                {
                    "track_id": track_id,
                    "before": {
                        "provider_track_id": before.provider_track_id if before else None,
                        "match_strategy": before.match_strategy if before else None,
                        "match_confidence": before.match_confidence if before else None,
                        "is_available": before.is_available if before else None,
                    },
                    "after": {
                        "provider_track_id": candidate.provider_track_id,
                        "match_strategy": candidate.match_strategy,
                        "match_confidence": candidate.match_confidence,
                        "is_available": candidate.is_available,
                    },
                }
            )
            time.sleep(self._rate_limit_seconds)
        return results

    def _audit_one(self, session: Session, track_id: int) -> DeezerAuditRow:
        preview = self._previews.get_for_track_provider(session, track_id=track_id, provider="deezer")
        download = self._downloads.get_latest_for_track(session, track_id)
        analysis_decision = analysis_decision_from_json(download.result_json if download else None)

        try:
            ctx = load_track_context(session, track_id)
        except Exception:
            return DeezerAuditRow(
                track_id=track_id,
                spotify_isrc=None,
                stored_deezer_id=preview.provider_track_id if preview else None,
                isrc_deezer_id=None,
                stored_title=preview.title if preview else None,
                isrc_title=None,
                stored_match_strategy=preview.match_strategy if preview else None,
                stored_match_confidence=float(preview.match_confidence) if preview and preview.match_confidence else None,
                analysis_decision=analysis_decision,
                verdict=VERDICT_NO_SPOTIFY_ISRC,
                details="track_not_found",
            )

        stored_conf = float(preview.match_confidence) if preview and preview.match_confidence is not None else None
        details: str | None = None
        isrc_hit = None
        if not ctx.isrc:
            verdict = VERDICT_NO_SPOTIFY_ISRC
        else:
            isrc_hit = self._client.get_track_by_isrc(ctx.isrc)
            verdict, details = classify_deezer_audit_verdict(
                preview=preview,
                isrc_hit=isrc_hit,
                stored_confidence=stored_conf,
            )

        return DeezerAuditRow(
            track_id=track_id,
            spotify_isrc=ctx.isrc,
            stored_deezer_id=preview.provider_track_id if preview else None,
            isrc_deezer_id=isrc_hit.id if isrc_hit else None,
            stored_title=preview.title if preview else None,
            isrc_title=isrc_hit.title if isrc_hit else None,
            stored_match_strategy=preview.match_strategy if preview else None,
            stored_match_confidence=stored_conf,
            analysis_decision=analysis_decision,
            verdict=verdict,
            details=details,
        )


def write_audit_csv(path: str, report: DeezerAuditReport) -> None:
    fieldnames = [
        "track_id",
        "spotify_isrc",
        "stored_deezer_id",
        "isrc_deezer_id",
        "stored_title",
        "isrc_title",
        "stored_match_strategy",
        "stored_match_confidence",
        "analysis_decision",
        "verdict",
        "details",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in report.rows:
            writer.writerow(asdict(row))
