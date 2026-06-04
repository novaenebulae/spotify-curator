from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AggregatedVector:
    vector: list[float]
    dimension: int
    segments_used: int
    segments_total: int
    confidence: float
    status: str


def validate_vector_dimension(vector: list[float], *, expected: int) -> None:
    if len(vector) != expected:
        raise ValueError(f"expected dimension {expected}, got {len(vector)}")


def aggregate_vectors(
    vectors: list[list[float]],
    *,
    expected_dimension: int,
) -> AggregatedVector | None:
    if not vectors:
        return None
    for vec in vectors:
        validate_vector_dimension(vec, expected=expected_dimension)

    segments_total = len(vectors)
    mean = [0.0] * expected_dimension
    for vec in vectors:
        for i, val in enumerate(vec):
            mean[i] += float(val)
    mean = [v / segments_total for v in mean]

    coverage = 1.0
    status = "success"
    return AggregatedVector(
        vector=mean,
        dimension=expected_dimension,
        segments_used=segments_total,
        segments_total=segments_total,
        confidence=min(1.0, 0.5 + 0.5 * coverage),
        status=status,
    )
