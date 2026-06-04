from __future__ import annotations

import math
from typing import Any

from app.features.advanced.raw_schemas import ClassifierSegmentOutput, MappedFeature

# model_key -> canonical feature name(s) produced
_MODEL_TO_FEATURES: dict[str, tuple[str, ...]] = {
    "mood_aggressive": ("mood_aggressive_score",),
    "mood_happy": ("mood_happy_score",),
    "mood_party": ("mood_party_score",),
    "mood_relaxed": ("mood_relaxed_score",),
    "mood_sad": ("mood_sad_score",),
    "mood_electronic": ("electronic_profile_score",),
    "mood_acoustic": ("acoustic_profile_score",),
    "approachability": ("approachability",),
    "engagement": ("engagement",),
    "danceability": ("danceability_tf",),
    "arousal_valence": ("arousal", "valence_tf"),
    "voice_instrumental": (
        "voice_probability",
        "vocal_presence_score",
        "instrumental_focus_score",
    ),
}

_BINARY_MODEL_KEYS = frozenset(
    {
        "mood_aggressive",
        "mood_happy",
        "mood_party",
        "mood_relaxed",
        "mood_sad",
        "mood_electronic",
        "mood_acoustic",
        "approachability",
        "engagement",
        "danceability",
    }
)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _sigmoid(logit: float) -> float:
    if logit >= 0:
        z = math.exp(-logit)
        return 1.0 / (1.0 + z)
    z = math.exp(logit)
    return z / (1.0 + z)


def binary_to_score(raw: float | dict[str, Any]) -> float:
    if isinstance(raw, dict):
        if "probability" in raw and raw["probability"] is not None:
            return _clamp01(float(raw["probability"]))
        if "logit" in raw and raw["logit"] is not None:
            return _sigmoid(float(raw["logit"]))
        if "score" in raw and raw["score"] is not None:
            return _clamp01(float(raw["score"]))
        raise ValueError("binary output missing probability/logit/score")
    return _clamp01(float(raw))


def regression_to_unit(raw: float | dict[str, Any], *, field: str) -> float:
    if isinstance(raw, dict):
        val = raw.get(field)
        if val is None:
            raise ValueError(f"regression output missing {field}")
        v = float(val)
    else:
        v = float(raw)
    # Essentia arousal/valence models often emit roughly -1..1 or 0..1
    if -1.05 <= v <= 1.05:
        return _clamp01((v + 1.0) / 2.0)
    return _clamp01(v)


def map_classifier_output(
    model_key: str,
    output: ClassifierSegmentOutput,
) -> list[MappedFeature]:
    if output.model_status != "available":
        return []
    confidence = 0.85
    results: list[MappedFeature] = []

    if model_key in _BINARY_MODEL_KEYS:
        if output.probability is None:
            return []
        score = _clamp01(output.probability)
        for name in _MODEL_TO_FEATURES.get(model_key, ()):
            results.append(
                MappedFeature(
                    feature_name=name,
                    value=score,
                    confidence=confidence,
                    model_key=model_key,
                    model_name=output.model_key,
                )
            )
        return results

    if model_key == "arousal_valence":
        if output.arousal is None or output.valence is None:
            return []
        arousal = regression_to_unit(output.arousal, field="arousal") if isinstance(
            output.arousal, dict
        ) else _clamp01((float(output.arousal) + 1.0) / 2.0 if -1.05 <= float(output.arousal) <= 1.05 else float(output.arousal))
        valence_tf = regression_to_unit(output.valence, field="valence") if isinstance(
            output.valence, dict
        ) else _clamp01(
            (float(output.valence) + 1.0) / 2.0
            if -1.05 <= float(output.valence) <= 1.05
            else float(output.valence)
        )
        results.append(
            MappedFeature(
                feature_name="arousal",
                value=arousal,
                confidence=confidence,
                model_key=model_key,
            )
        )
        results.append(
            MappedFeature(
                feature_name="valence_tf",
                value=valence_tf,
                confidence=confidence,
                model_key=model_key,
            )
        )
        return results

    if model_key == "voice_instrumental":
        voice = output.voice_probability
        instr = output.instrumental_probability
        if voice is None or instr is None:
            return []
        voice_p = _clamp01(voice)
        instr_p = _clamp01(instr)
        vocal = _clamp01(voice_p * (1.0 - instr_p * 0.5))
        instrumental_focus = _clamp01(instr_p * (1.0 - voice_p * 0.3))
        results.extend(
            [
                MappedFeature(
                    feature_name="voice_probability",
                    value=voice_p,
                    confidence=confidence,
                    model_key=model_key,
                ),
                MappedFeature(
                    feature_name="vocal_presence_score",
                    value=vocal,
                    confidence=confidence,
                    model_key=model_key,
                ),
                MappedFeature(
                    feature_name="instrumental_focus_score",
                    value=instrumental_focus,
                    confidence=confidence,
                    model_key=model_key,
                ),
            ]
        )
        return results

    return results


def map_segment_outputs_to_features(
    classifier_outputs: dict[str, dict[str, Any]],
) -> list[MappedFeature]:
    mapped: list[MappedFeature] = []
    for model_key, payload in classifier_outputs.items():
        if not isinstance(payload, dict):
            continue
        output = ClassifierSegmentOutput(
            model_key=str(payload.get("model_key") or model_key),
            model_status=payload.get("model_status", "available"),  # type: ignore[arg-type]
            probability=payload.get("probability"),
            arousal=payload.get("arousal"),
            valence=payload.get("valence"),
            voice_probability=payload.get("voice_probability"),
            instrumental_probability=payload.get("instrumental_probability"),
            raw=payload,
        )
        mapped.extend(map_classifier_output(model_key, output))
    return mapped


def classifier_model_keys() -> frozenset[str]:
    return frozenset(_MODEL_TO_FEATURES.keys())


def feature_names_for_model_key(model_key: str) -> tuple[str, ...]:
    return _MODEL_TO_FEATURES.get(model_key, ())
