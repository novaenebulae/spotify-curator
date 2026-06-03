from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExclusionReason:
    code: str
    message: str
    field: str | None = None
    value: Any = None
    expected: dict[str, Any] | None = None


@dataclass
class TrackExclusion:
    track_id: int
    excluded: bool = True
    reasons: list[ExclusionReason] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "excluded": self.excluded,
            "reasons": [
                {
                    "code": r.code,
                    "message": r.message,
                    "field": r.field,
                    "value": r.value,
                    "expected": r.expected,
                }
                for r in self.reasons
            ],
        }
