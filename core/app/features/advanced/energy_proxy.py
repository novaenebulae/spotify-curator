from __future__ import annotations

from typing import Any

from app.audio.essentia_aggregate import AggregatedFeatures
from app.settings.config import settings


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _normalize_loudness_db(loudness_db: float) -> float:
    """Map loudness dB (-60..0 typical) to 0..1 energy contribution."""
    return _clamp01((float(loudness_db) + 60.0) / 60.0)


def _normalize_dynamic_complexity(value: float) -> float:
    """Heuristic cap: Essentia dynamic complexity often in ~0..20."""
    return _clamp01(float(value) / 15.0)


def _normalize_onset_rate(value: float) -> float:
    """Heuristic cap for onset rate."""
    return _clamp01(float(value) / 8.0)


def compute_energy_proxy(
    lowlevel: AggregatedFeatures | dict[str, Any],
    *,
    enabled: bool | None = None,
) -> tuple[float | None, float | None]:
    """
    Derive energy_proxy from aggregated low-level descriptors.

    Returns (value 0..1, confidence 0..1) or (None, None) if insufficient data.
    """
    if enabled is None:
        enabled = settings.energy_proxy_enabled
    if not enabled:
        return None, None

    if isinstance(lowlevel, AggregatedFeatures):
        loudness = lowlevel.loudness
        dynamic = lowlevel.dynamic_complexity
        onset = lowlevel.onset_rate
    else:
        loudness = lowlevel.get("loudness") or lowlevel.get("loudness_db")
        dynamic = lowlevel.get("dynamic_complexity")
        onset = lowlevel.get("onset_rate")

    components: list[tuple[float, float]] = []
    if loudness is not None:
        components.append((_normalize_loudness_db(float(loudness)), 0.45))
    if dynamic is not None:
        components.append((_normalize_dynamic_complexity(float(dynamic)), 0.35))
    if onset is not None:
        components.append((_normalize_onset_rate(float(onset)), 0.20))

    if not components:
        return None, None

    weight_sum = sum(w for _, w in components)
    value = sum(v * w for v, w in components) / weight_sum
    # Confidence scales with how many inputs contributed
    confidence = _clamp01(0.5 + 0.5 * (len(components) / 3.0))
    return _clamp01(value), confidence
