from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from app.settings.config import settings

LICENSE_NAME = "CC BY-NC-SA 4.0"
_PACKAGED_MANIFEST = Path(__file__).resolve().parent / "essentia_models_manifest.yaml"

ManifestModelStatus = Literal[
    "available",
    "missing",
    "metadata_missing",
    "weights_missing",
    "invalid_hash",
    "disabled",
]


class ModelManagerError(Exception):
    """Domain error raised by ModelManager; mapped to ApiError at the API layer."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


@dataclass(frozen=True)
class ModelEntry:
    model_key: str
    display_name: str
    task: str
    weights_url: str
    metadata_url: str
    local_weights_path: str
    local_metadata_path: str
    depends_on: tuple[str, ...] = ()
    required_for: tuple[str, ...] = ()
    license: str = LICENSE_NAME
    expected_sha256: str | None = None
    size_bytes: int | None = None
    output: str | None = None
    sample_rate: int | None = None
    backend: str | None = None


def _http_download(url: str, dest: Path, timeout: int) -> int:
    """Stream a remote file to disk. Network access; mocked in tests."""
    import httpx

    dest.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as resp:
        resp.raise_for_status()
        with dest.open("wb") as handle:
            for chunk in resp.iter_bytes():
                handle.write(chunk)
                total += len(chunk)
    return total


class ModelManager:
    """Manifest-driven management of Essentia TensorFlow models (phase 6.8A)."""

    def __init__(
        self,
        *,
        models_dir: str | None = None,
        manifest_path: str | None = None,
        verify_hash: bool | None = None,
        downloader=None,
    ) -> None:
        self._models_dir = Path(models_dir or settings.essentia_models_dir)
        self._manifest_path = self._resolve_manifest_path(manifest_path)
        self._verify_hash = (
            verify_hash if verify_hash is not None else settings.essentia_models_verify_hash
        )
        self._downloader = downloader
        self._license: dict[str, Any] = {}
        self._default_profile: str = settings.essentia_models_default_profile
        self._models: dict[str, ModelEntry] = {}
        self._profiles: dict[str, dict[str, Any]] = {}
        self._load_manifest()

    # ----- manifest loading -------------------------------------------------

    @staticmethod
    def _resolve_manifest_path(manifest_path: str | None) -> Path:
        candidate = Path(manifest_path or settings.essentia_models_manifest)
        if candidate.is_file():
            return candidate
        if _PACKAGED_MANIFEST.is_file():
            return _PACKAGED_MANIFEST
        return candidate

    def _load_manifest(self) -> None:
        if not self._manifest_path.is_file():
            raise ModelManagerError(
                code="MODEL_MANIFEST_MISSING",
                message=f"Essentia models manifest not found: {self._manifest_path}",
                status_code=500,
            )
        raw = yaml.safe_load(self._manifest_path.read_text(encoding="utf-8")) or {}
        self._license = raw.get("license") or {"name": LICENSE_NAME}
        self._default_profile = str(raw.get("default_profile") or self._default_profile)
        self._profiles = dict(raw.get("profiles") or {})
        models: dict[str, ModelEntry] = {}
        for key, value in (raw.get("models") or {}).items():
            models[str(key)] = ModelEntry(
                model_key=str(key),
                display_name=str(value.get("display_name") or key),
                task=str(value.get("task") or "unknown"),
                weights_url=str(value.get("weights_url") or ""),
                metadata_url=str(value.get("metadata_url") or ""),
                local_weights_path=str(value.get("local_weights_path") or ""),
                local_metadata_path=str(value.get("local_metadata_path") or ""),
                depends_on=tuple(value.get("depends_on") or ()),
                required_for=tuple(value.get("required_for") or ()),
                license=str(value.get("license") or LICENSE_NAME),
                expected_sha256=(
                    str(value["expected_sha256"]).strip().lower()
                    if value.get("expected_sha256")
                    else None
                ),
                size_bytes=value.get("size_bytes"),
                output=(str(value["output"]) if value.get("output") else None),
                sample_rate=value.get("sample_rate"),
                backend=(str(value["backend"]) if value.get("backend") else None),
            )
        self._models = models

    # ----- listing ----------------------------------------------------------

    def list_models(self) -> list[ModelEntry]:
        return list(self._models.values())

    def list_profiles(self) -> list[str]:
        return list(self._profiles.keys())

    @property
    def license(self) -> dict[str, Any]:
        return dict(self._license)

    @property
    def default_profile(self) -> str:
        return self._default_profile

    def _require_model(self, model_key: str) -> ModelEntry:
        entry = self._models.get(model_key)
        if entry is None:
            raise ModelManagerError(
                code="MODEL_MISSING",
                message=f"Unknown model_key: {model_key}",
                status_code=404,
            )
        return entry

    def get_entry(self, model_key: str) -> ModelEntry:
        """Public accessor for a manifest model entry (raises if unknown)."""
        return self._require_model(model_key)

    def weights_path(self, model_key: str) -> Path:
        """Absolute path to the model weights file (.pb)."""
        return self._paths_for(self._require_model(model_key))[0]

    def metadata_path(self, model_key: str) -> Path:
        """Absolute path to the model metadata file (.json)."""
        return self._paths_for(self._require_model(model_key))[1]

    def is_available(self, model_key: str) -> bool:
        """True only when weights + metadata exist and the hash check passes."""
        status, _ = self._status_for(self._require_model(model_key))
        return status == "available"

    def resolve_profile(self, profile: str) -> list[str]:
        """Resolve a profile to an ordered, de-duplicated list of model keys (deps first)."""
        if profile not in self._profiles:
            raise ModelManagerError(
                code="PROFILE_NOT_FOUND",
                message=f"Unknown profile: {profile}",
                status_code=404,
            )
        collected: list[str] = []
        seen: set[str] = set()

        def _add(key: str) -> None:
            entry = self._models.get(key)
            if entry is not None:
                for dep in entry.depends_on:
                    _add(dep)
            if key not in seen:
                seen.add(key)
                collected.append(key)

        def _walk_profile(name: str, guard: set[str]) -> None:
            if name in guard:
                return
            guard.add(name)
            spec = self._profiles.get(name) or {}
            parent = spec.get("extends")
            if parent:
                _walk_profile(str(parent), guard)
            for key in spec.get("models") or []:
                _add(str(key))

        _walk_profile(profile, set())
        return collected

    # ----- status -----------------------------------------------------------

    @staticmethod
    def compute_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _paths_for(self, entry: ModelEntry) -> tuple[Path, Path]:
        """Resolve weights/metadata under essentia_models_dir (avoid essentia/essentia/)."""
        weights_rel = entry.local_weights_path
        metadata_rel = entry.local_metadata_path
        if weights_rel.startswith("essentia/") and self._models_dir.name == "essentia":
            weights_rel = weights_rel.removeprefix("essentia/")
            metadata_rel = metadata_rel.removeprefix("essentia/")
        weights = self._models_dir / weights_rel
        metadata = self._models_dir / metadata_rel
        if not weights.is_file() and entry.local_weights_path != weights_rel:
            alt_w = self._models_dir / entry.local_weights_path
            alt_m = self._models_dir / entry.local_metadata_path
            if alt_w.is_file() and alt_m.is_file():
                return alt_w, alt_m
        return weights, metadata

    def _status_for(self, entry: ModelEntry) -> tuple[ManifestModelStatus, str | None]:
        weights, metadata = self._paths_for(entry)
        has_weights = weights.is_file()
        has_metadata = metadata.is_file()
        if not has_weights and not has_metadata:
            return "missing", None
        if has_weights and not has_metadata:
            return "metadata_missing", None
        if has_metadata and not has_weights:
            return "weights_missing", None
        sha256 = self.compute_sha256(weights)
        if self._verify_hash and entry.expected_sha256 and sha256 != entry.expected_sha256:
            return "invalid_hash", sha256
        return "available", sha256

    def get_model_status(self, model_key: str) -> dict[str, Any]:
        entry = self._require_model(model_key)
        status, sha256 = self._status_for(entry)
        return {
            "model_key": entry.model_key,
            "display_name": entry.display_name,
            "task": entry.task,
            "status": status,
            "required_for": list(entry.required_for),
            "license": entry.license,
            "local_weights_path": entry.local_weights_path,
            "local_metadata_path": entry.local_metadata_path,
            "sha256": sha256,
            "expected_sha256": entry.expected_sha256,
            "size_bytes": entry.size_bytes,
        }

    def _profile_status(self, profile: str, available: set[str]) -> dict[str, Any]:
        keys = self.resolve_profile(profile)
        avail = sum(1 for k in keys if k in available)
        missing = len(keys) - avail
        if missing == 0:
            status = "available"
        elif avail == 0:
            status = "missing"
        else:
            status = "partial"
        return {
            "name": profile,
            "status": status,
            "available_count": avail,
            "missing_count": missing,
            "description": str((self._profiles.get(profile) or {}).get("description") or ""),
        }

    def get_status(self) -> dict[str, Any]:
        models = [self.get_model_status(key) for key in self._models]
        available = {m["model_key"] for m in models if m["status"] == "available"}
        counts = {"available": 0, "missing": 0, "invalid_hash": 0, "disabled": 0}
        for row in models:
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        real_ready = False
        if "phase6-minimal" in self._profiles:
            minimal_keys = self.resolve_profile("phase6-minimal")
            real_ready = bool(minimal_keys) and all(k in available for k in minimal_keys)
        profiles = [self._profile_status(name, available) for name in self._profiles]
        summary = {
            "total": len(models),
            "available": counts.get("available", 0),
            "missing": counts.get("missing", 0),
            "invalid_hash": counts.get("invalid_hash", 0),
            "disabled": counts.get("disabled", 0),
            "real_inference_ready": real_ready,
            "default_profile": self._default_profile,
        }
        return {"summary": summary, "profiles": profiles, "models": models}

    def read_metadata(self, model_key: str) -> dict[str, Any] | None:
        entry = self._require_model(model_key)
        _, metadata = self._paths_for(entry)
        if not metadata.is_file():
            return None
        try:
            return json.loads(metadata.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    # ----- license + download ----------------------------------------------

    def _ensure_license(self, accept_license: bool) -> None:
        if accept_license or settings.essentia_models_accept_license:
            return
        raise ModelManagerError(
            code="MODEL_LICENSE_NOT_ACCEPTED",
            message=(
                "Model download requires accepting the declared model license "
                f"({self._license.get('name', LICENSE_NAME)})."
            ),
            status_code=403,
            details={"license": self._license.get("name", LICENSE_NAME)},
        )

    def _do_download(self, url: str, dest: Path) -> int:
        downloader = self._downloader or _http_download
        try:
            return downloader(url, dest, settings.essentia_models_download_timeout_seconds)
        except ModelManagerError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalize to domain error
            raise ModelManagerError(
                code="MODEL_DOWNLOAD_FAILED",
                message=f"Download failed for {url}: {exc}",
                status_code=502,
                details={"url": url},
            ) from exc

    def download_model(
        self, model_key: str, *, accept_license: bool, force: bool = False
    ) -> dict[str, Any]:
        self._ensure_license(accept_license)
        # Download the model and its dependency chain (extractor before head).
        keys: list[str] = []
        seen: set[str] = set()

        def _add(key: str) -> None:
            entry = self._models.get(key)
            if entry is None:
                return
            for dep in entry.depends_on:
                _add(dep)
            if key not in seen:
                seen.add(key)
                keys.append(key)

        self._require_model(model_key)
        _add(model_key)
        downloaded = [self._download_one(k, force=force) for k in keys]
        return {"model_key": model_key, "downloaded": downloaded}

    def download_profile(
        self, profile: str, *, accept_license: bool, force: bool = False
    ) -> dict[str, Any]:
        self._ensure_license(accept_license)
        keys = self.resolve_profile(profile)
        downloaded = [self._download_one(k, force=force) for k in keys]
        return {"profile": profile, "models": downloaded}

    def _download_one(self, model_key: str, *, force: bool) -> dict[str, Any]:
        entry = self._require_model(model_key)
        weights, metadata = self._paths_for(entry)
        actions: list[str] = []
        if force or not weights.is_file():
            self._do_download(entry.weights_url, weights)
            actions.append("weights")
        if force or not metadata.is_file():
            self._do_download(entry.metadata_url, metadata)
            actions.append("metadata")
        status, sha256 = self._status_for(entry)
        return {
            "model_key": model_key,
            "status": status,
            "sha256": sha256,
            "downloaded": actions,
        }

    # ----- verification -----------------------------------------------------

    def verify_model(self, model_key: str) -> dict[str, Any]:
        entry = self._require_model(model_key)
        weights, metadata = self._paths_for(entry)
        status, sha256 = self._status_for(entry)
        return {
            "model_key": model_key,
            "status": status,
            "weights_exists": weights.is_file(),
            "metadata_exists": metadata.is_file(),
            "sha256": sha256,
            "expected_sha256": entry.expected_sha256,
        }

    def verify_profile(self, profile: str) -> dict[str, Any]:
        keys = self.resolve_profile(profile)
        return {"profile": profile, "models": [self.verify_model(k) for k in keys]}
