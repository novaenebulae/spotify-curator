from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from app.models_registry.manager import ModelManager, ModelManagerError

EFFNET_WEIGHTS = "essentia/feature-extractors/discogs-effnet/discogs-effnet-bs64-1.pb"
EFFNET_METADATA = "essentia/feature-extractors/discogs-effnet/discogs-effnet-bs64-1.json"


def _fake_downloader(payloads: dict[str, bytes] | None = None):
    payloads = payloads or {}

    def _dl(url: str, dest: Path, timeout: int) -> int:
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = payloads.get(url, b"fake-bytes")
        dest.write_bytes(data)
        return len(data)

    return _dl


def _write_custom_manifest(tmp_path: Path, *, expected_sha256: str | None = None) -> Path:
    manifest = {
        "license": {"name": "CC BY-NC-SA 4.0"},
        "default_profile": "phase6-minimal",
        "profiles": {
            "phase6-minimal": {"description": "min", "models": ["discogs_effnet_bs64"]},
        },
        "models": {
            "discogs_effnet_bs64": {
                "display_name": "Discogs EffNet BS64",
                "task": "embedding",
                "weights_url": "https://example.test/effnet.pb",
                "metadata_url": "https://example.test/effnet.json",
                "local_weights_path": EFFNET_WEIGHTS,
                "local_metadata_path": EFFNET_METADATA,
                "required_for": ["style_embedding"],
                "expected_sha256": expected_sha256,
                "size_bytes": 10,
            }
        },
    }
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    return path


def test_status_missing(tmp_path) -> None:
    manifest = _write_custom_manifest(tmp_path)
    mgr = ModelManager(models_dir=str(tmp_path / "models"), manifest_path=str(manifest))
    assert mgr.get_model_status("discogs_effnet_bs64")["status"] == "missing"


def test_status_metadata_missing(tmp_path) -> None:
    manifest = _write_custom_manifest(tmp_path)
    models_dir = tmp_path / "models"
    weights = models_dir / EFFNET_WEIGHTS
    weights.parent.mkdir(parents=True)
    weights.write_bytes(b"weights")
    mgr = ModelManager(models_dir=str(models_dir), manifest_path=str(manifest))
    assert mgr.get_model_status("discogs_effnet_bs64")["status"] == "metadata_missing"


def test_status_weights_missing(tmp_path) -> None:
    manifest = _write_custom_manifest(tmp_path)
    models_dir = tmp_path / "models"
    metadata = models_dir / EFFNET_METADATA
    metadata.parent.mkdir(parents=True)
    metadata.write_text("{}", encoding="utf-8")
    mgr = ModelManager(models_dir=str(models_dir), manifest_path=str(manifest))
    assert mgr.get_model_status("discogs_effnet_bs64")["status"] == "weights_missing"


def test_status_available_with_sha256(tmp_path) -> None:
    manifest = _write_custom_manifest(tmp_path)
    models_dir = tmp_path / "models"
    weights = models_dir / EFFNET_WEIGHTS
    weights.parent.mkdir(parents=True)
    weights.write_bytes(b"weights")
    (models_dir / EFFNET_METADATA).write_text("{}", encoding="utf-8")
    mgr = ModelManager(models_dir=str(models_dir), manifest_path=str(manifest))
    row = mgr.get_model_status("discogs_effnet_bs64")
    assert row["status"] == "available"
    assert row["sha256"] == hashlib.sha256(b"weights").hexdigest()


def test_status_invalid_hash(tmp_path) -> None:
    manifest = _write_custom_manifest(tmp_path, expected_sha256="0" * 64)
    models_dir = tmp_path / "models"
    weights = models_dir / EFFNET_WEIGHTS
    weights.parent.mkdir(parents=True)
    weights.write_bytes(b"weights")
    (models_dir / EFFNET_METADATA).write_text("{}", encoding="utf-8")
    mgr = ModelManager(models_dir=str(models_dir), manifest_path=str(manifest))
    assert mgr.get_model_status("discogs_effnet_bs64")["status"] == "invalid_hash"


def test_download_profile_minimal_excludes_maest(tmp_path) -> None:
    models_dir = tmp_path / "models"
    mgr = ModelManager(
        models_dir=str(models_dir),
        downloader=_fake_downloader(),
    )
    result = mgr.download_profile("phase6-minimal", accept_license=True)
    keys = [row["model_key"] for row in result["models"]]
    assert "discogs_effnet_bs64" in keys
    assert "discogs_maest_30s_pw_519l" not in keys
    assert len(keys) == 12
    for row in result["models"]:
        assert row["status"] == "available"


def test_download_profile_recommended_includes_maest(tmp_path) -> None:
    models_dir = tmp_path / "models"
    mgr = ModelManager(models_dir=str(models_dir), downloader=_fake_downloader())
    result = mgr.download_profile("phase6-recommended", accept_license=True)
    keys = [row["model_key"] for row in result["models"]]
    assert "discogs_maest_30s_pw_519l" in keys
    assert "genre_discogs519_maest_519l" in keys


def test_download_requires_license(tmp_path) -> None:
    mgr = ModelManager(models_dir=str(tmp_path / "models"), downloader=_fake_downloader())
    try:
        mgr.download_profile("phase6-minimal", accept_license=False)
    except ModelManagerError as exc:
        assert exc.code == "MODEL_LICENSE_NOT_ACCEPTED"
    else:
        raise AssertionError("expected ModelManagerError")


def test_verify_profile_reports_status(tmp_path) -> None:
    models_dir = tmp_path / "models"
    mgr = ModelManager(models_dir=str(models_dir), downloader=_fake_downloader())
    report = mgr.verify_profile("phase6-minimal")
    assert all(row["status"] == "missing" for row in report["models"])
