from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from app.models_registry.definitions import MODEL_DEFINITIONS, REQUIRED_MODEL_KEYS
from app.models_registry.types import ModelDefinition, ModelStatus, ModelStatusSummary
from app.settings.config import settings


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ModelRegistry:
    def __init__(
        self,
        *,
        models_dir: str | None = None,
        manifest_path: str | None = None,
        hash_check_enabled: bool | None = None,
    ) -> None:
        self._models_dir = Path(models_dir or settings.models_dir)
        self._manifest_path = Path(manifest_path or settings.model_registry_path)
        self._hash_check = (
            hash_check_enabled
            if hash_check_enabled is not None
            else settings.model_hash_check_enabled
        )

    def scan(self) -> tuple[list[ModelStatus], ModelStatusSummary]:
        now = datetime.now(tz=UTC).replace(tzinfo=None).isoformat()
        manifest = self._load_manifest()
        statuses: list[ModelStatus] = []

        for definition in MODEL_DEFINITIONS:
            statuses.append(self._inspect_definition(definition, manifest, now))

        counts = {"available": 0, "missing": 0, "invalid_hash": 0, "disabled": 0}
        for row in statuses:
            counts[row.status] = counts.get(row.status, 0) + 1
        summary = ModelStatusSummary(
            available=counts["available"],
            missing=counts["missing"],
            invalid_hash=counts["invalid_hash"],
            disabled=counts["disabled"],
        )

        return statuses, summary

    def has_required_models(self) -> bool:
        statuses, _ = self.scan()
        available = {s.model_key for s in statuses if s.status == "available"}
        return REQUIRED_MODEL_KEYS.issubset(available)

    def should_run_status_only(self) -> bool:
        if settings.essentia_tensorflow_status_only:
            return True
        return not self.has_required_models()

    def _load_manifest(self) -> dict[str, dict]:
        if not self._manifest_path.is_file():
            return {}
        try:
            raw = json.loads(self._manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        models = raw.get("models") if isinstance(raw, dict) else raw
        if not isinstance(models, dict):
            return {}
        return {str(k): v for k, v in models.items() if isinstance(v, dict)}

    def _inspect_definition(
        self,
        definition: ModelDefinition,
        manifest: dict[str, dict],
        checked_at: str,
    ) -> ModelStatus:
        if not definition.enabled:
            return ModelStatus(
                model_key=definition.model_key,
                model_name=definition.model_name,
                task_type=definition.task_type,
                status="disabled",
                version=definition.version,
                relative_path=definition.relative_path,
                dimension=definition.dimension,
                last_checked_at=checked_at,
            )

        entry = manifest.get(definition.model_key, {})
        rel = str(entry.get("relative_path") or definition.relative_path)
        path = self._models_dir / rel
        expected_hash = entry.get("sha256") if self._hash_check else None
        if isinstance(expected_hash, str):
            expected_hash = expected_hash.strip().lower() or None

        if not path.is_file():
            return ModelStatus(
                model_key=definition.model_key,
                model_name=definition.model_name,
                task_type=definition.task_type,
                status="missing",
                version=str(entry.get("version") or definition.version),
                relative_path=rel,
                dimension=definition.dimension,
                last_checked_at=checked_at,
            )

        sha256: str | None = None
        status = "available"
        error_message: str | None = None
        try:
            sha256 = _sha256_file(path)
            if expected_hash and sha256 != expected_hash:
                status = "invalid_hash"
                error_message = "sha256 mismatch"
        except OSError as e:
            status = "missing"
            error_message = str(e)[:200]

        return ModelStatus(
            model_key=definition.model_key,
            model_name=definition.model_name,
            task_type=definition.task_type,
            status=status,  # type: ignore[arg-type]
            version=str(entry.get("version") or definition.version),
            relative_path=rel,
            sha256=sha256,
            dimension=definition.dimension,
            last_checked_at=checked_at,
            error_message=error_message,
        )
