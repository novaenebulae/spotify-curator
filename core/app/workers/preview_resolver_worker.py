from __future__ import annotations

from sqlalchemy.orm import Session

from app.audio.track_context import load_track_context
from app.database.engine import get_engine
from app.jobs.items.constants import WORKER_TYPE_PREVIEW_RESOLVER
from app.jobs.items.service import ReservedJobItem
from app.previews.deezer_provider import DeezerPreviewProvider
from app.previews.upsert import PreviewUpsertService
from app.workers.base_worker import BaseWorker


class PreviewResolverWorker(BaseWorker):
    worker_type = WORKER_TYPE_PREVIEW_RESOLVER

    def __init__(
        self,
        *,
        provider: DeezerPreviewProvider | None = None,
        upsert: PreviewUpsertService | None = None,
    ) -> None:
        super().__init__()
        self._provider = provider or DeezerPreviewProvider()
        self._upsert = upsert or PreviewUpsertService()

    def process_item(self, item: object) -> None:
        assert isinstance(item, ReservedJobItem)
        if item.track_id is None:
            self._items.mark_failed(
                item.id, error_code="INVALID_ITEM", error_message="Missing track_id"
            )
            return
        engine = get_engine()
        with Session(engine) as session:
            ctx = load_track_context(session, item.track_id)
        candidate = self._provider.resolve_preview(ctx)
        with Session(engine) as session:
            self._upsert.upsert_candidate(session, track_id=item.track_id, candidate=candidate)
            session.commit()
        self._items.mark_success(
            item.id,
            result_json={
                "is_available": candidate.is_available,
                "match_confidence": candidate.match_confidence,
            },
        )
