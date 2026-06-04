from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ModelAvailabilityStatus = Literal["available", "missing", "invalid_hash", "disabled"]


@dataclass(frozen=True)
class ModelDefinition:
    model_key: str
    model_name: str
    task_type: str
    relative_path: str
    version: str = "1"
    dimension: int | None = None
    required_for_inference: bool = True
    enabled: bool = True


@dataclass(frozen=True)
class ModelStatus:
    model_key: str
    model_name: str
    task_type: str
    status: ModelAvailabilityStatus
    version: str
    relative_path: str
    sha256: str | None = None
    dimension: int | None = None
    last_checked_at: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict:
        return {
            "model_key": self.model_key,
            "model_name": self.model_name,
            "task_type": self.task_type,
            "status": self.status,
            "version": self.version,
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "dimension": self.dimension,
            "last_checked_at": self.last_checked_at,
            "error_message": self.error_message,
        }


@dataclass(frozen=True)
class ModelStatusSummary:
    available: int = 0
    missing: int = 0
    invalid_hash: int = 0
    disabled: int = 0

    def to_dict(self) -> dict:
        return {
            "available": self.available,
            "missing": self.missing,
            "invalid_hash": self.invalid_hash,
            "disabled": self.disabled,
        }
