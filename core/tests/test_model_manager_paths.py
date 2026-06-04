from __future__ import annotations

from pathlib import Path

import pytest

from app.models_registry.manager import ModelEntry, ModelManager


def test_paths_for_strips_duplicate_essentia_prefix(tmp_path, monkeypatch) -> None:
    root = tmp_path / "essentia"
    weights_dir = root / "feature-extractors" / "maest"
    weights_dir.mkdir(parents=True)
    weights = weights_dir / "model.pb"
    weights.write_bytes(b"x")
    meta = weights_dir / "model.json"
    meta.write_text("{}", encoding="utf-8")

    monkeypatch.setenv("ESSENTIA_MODELS_DIR", str(root))
    mm = ModelManager(models_dir=str(root))
    entry = ModelEntry(
        model_key="test_maest",
        display_name="Test",
        task="embeddings",
        weights_url="http://example.com/w.pb",
        metadata_url="http://example.com/m.json",
        local_weights_path="essentia/feature-extractors/maest/model.pb",
        local_metadata_path="essentia/feature-extractors/maest/model.json",
    )
    w, m = mm._paths_for(entry)
    assert w.is_file()
    assert m.is_file()
