from __future__ import annotations

import json
from pathlib import Path

from app.models_registry import ModelRegistry
from app.models_registry.definitions import MODEL_DEFINITIONS


def test_registry_reports_missing_models(tmp_path) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    registry = ModelRegistry(models_dir=str(models_dir), manifest_path=str(tmp_path / "none.json"))
    rows, summary = registry.scan()
    assert len(rows) == len(MODEL_DEFINITIONS)
    assert summary.missing > 0
    assert summary.available == 0
    assert not registry.has_required_models()
    assert registry.should_run_status_only()


def test_registry_available_with_valid_hash(tmp_path, monkeypatch) -> None:
    models_dir = tmp_path / "models"
    effnet_path = models_dir / "discogs_effnet" / "discogs-effnet-bs64-1.pb"
    effnet_path.parent.mkdir(parents=True)
    effnet_path.write_bytes(b"fake-model-bytes")

    genre_path = models_dir / "discogs_maest" / "genre_discogs519-discogs-maest-30s-pw-519l.pb"
    genre_path.parent.mkdir(parents=True, exist_ok=True)
    genre_path.write_bytes(b"genre-model")

    manifest = {
        "models": {
            "discogs_effnet_embeddings": {
                "relative_path": "discogs_effnet/discogs-effnet-bs64-1.pb",
                "sha256": _sha256(effnet_path),
            },
            "genre_discogs_519": {
                "relative_path": "discogs_maest/genre_discogs519-discogs-maest-30s-pw-519l.pb",
            },
        }
    }
    manifest_path = tmp_path / "model_registry.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    registry = ModelRegistry(models_dir=str(models_dir), manifest_path=str(manifest_path))
    rows, summary = registry.scan()
    assert summary.available >= 2
    assert registry.has_required_models()
    assert not registry.should_run_status_only()


def test_registry_invalid_hash(tmp_path) -> None:
    models_dir = tmp_path / "models"
    effnet_path = models_dir / "discogs_effnet" / "discogs-effnet-bs64-1.pb"
    effnet_path.parent.mkdir(parents=True)
    effnet_path.write_bytes(b"wrong-content")

    manifest_path = tmp_path / "model_registry.json"
    manifest_path.write_text(
        json.dumps(
            {
                "models": {
                    "discogs_effnet_embeddings": {
                        "relative_path": "discogs_effnet/discogs-effnet-bs64-1.pb",
                        "sha256": "0" * 64,
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    registry = ModelRegistry(models_dir=str(models_dir), manifest_path=str(manifest_path))
    rows, summary = registry.scan()
    effnet = next(r for r in rows if r.model_key == "discogs_effnet_embeddings")
    assert effnet.status == "invalid_hash"
    assert summary.invalid_hash >= 1
    assert not registry.has_required_models()


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
