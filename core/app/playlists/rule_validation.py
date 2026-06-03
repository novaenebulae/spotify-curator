from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from app.playlists.feature_registry import FeatureRegistry, get_feature_registry
from app.playlists.rule_schemas import (
    FUTURE_ORDERING_MODES,
    PlaylistRule,
    PlaylistRuleValidateResponse,
    ValidationIssue,
)

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


class PlaylistRuleValidator:
    def __init__(self, *, registry: FeatureRegistry | None = None) -> None:
        self._registry = registry or get_feature_registry()

    def validate(
        self,
        *,
        rule: dict[str, Any] | None = None,
        rule_yaml: str | None = None,
    ) -> PlaylistRuleValidateResponse:
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []

        raw = rule
        if rule_yaml is not None:
            if yaml is None:
                errors.append(
                    ValidationIssue(
                        code="RULE_INVALID_YAML",
                        message="YAML support requires PyYAML",
                        path="rule_yaml",
                    )
                )
                return PlaylistRuleValidateResponse(valid=False, errors=errors, warnings=warnings)
            try:
                raw = yaml.safe_load(rule_yaml)
            except Exception as exc:
                errors.append(
                    ValidationIssue(
                        code="RULE_INVALID_YAML",
                        message=str(exc),
                        path="rule_yaml",
                    )
                )
                return PlaylistRuleValidateResponse(valid=False, errors=errors, warnings=warnings)

        if raw is None:
            errors.append(
                ValidationIssue(code="RULE_INVALID_SCHEMA", message="rule or rule_yaml required")
            )
            return PlaylistRuleValidateResponse(valid=False, errors=errors, warnings=warnings)

        if not isinstance(raw, dict):
            errors.append(
                ValidationIssue(code="RULE_INVALID_SCHEMA", message="rule must be a JSON object")
            )
            return PlaylistRuleValidateResponse(valid=False, errors=errors, warnings=warnings)

        try:
            parsed = PlaylistRule.model_validate(raw)
        except ValidationError as exc:
            for err in exc.errors():
                code = "RULE_INVALID_SCHEMA"
                msg = err.get("msg", "invalid")
                if "TARGET_SIZE_INVALID" in str(msg):
                    code = "TARGET_SIZE_INVALID"
                errors.append(
                    ValidationIssue(
                        code=code,
                        message=str(msg),
                        path=".".join(str(p) for p in err.get("loc", ())),
                    )
                )
            return PlaylistRuleValidateResponse(valid=False, errors=errors, warnings=warnings)
        except ValueError as exc:
            code = str(exc) if str(exc).isupper() else "RULE_INVALID_SCHEMA"
            errors.append(ValidationIssue(code=code, message=str(exc)))
            return PlaylistRuleValidateResponse(valid=False, errors=errors, warnings=warnings)

        self._validate_source(parsed, errors, warnings)
        self._validate_features(parsed, errors, warnings)
        self._validate_weights(parsed, errors, warnings)
        self._validate_ordering(parsed, errors, warnings)
        self._validate_sync(parsed, errors, warnings)
        self._validate_future_fields(parsed, warnings)

        valid = len(errors) == 0
        return PlaylistRuleValidateResponse(
            valid=valid,
            errors=errors,
            warnings=warnings,
            normalized_rule=parsed.model_dump_normalized() if valid else None,
        )

    def _validate_source(
        self,
        rule: PlaylistRule,
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
    ) -> None:
        src = rule.source
        has_source = (
            src.liked_tracks
            or src.playlists_include
            or src.track_ids_include
        )
        if not has_source:
            errors.append(
                ValidationIssue(
                    code="NO_SOURCE_SELECTED",
                    message="At least one source must be selected",
                    path="source",
                )
            )
        if src.clusters_include or src.clusters_exclude:
            warnings.append(
                ValidationIssue(
                    code="CLUSTER_SOURCE_NOT_AVAILABLE_YET",
                    message="Cluster sources are not available until phase 6",
                    path="source",
                )
            )
        if src.seed_tracks:
            warnings.append(
                ValidationIssue(
                    code="SEED_TRACKS_NOT_AVAILABLE_IN_PHASE_5",
                    message="Seed tracks are not available in phase 5",
                    path="source.seed_tracks",
                )
            )

    def _validate_features(
        self,
        rule: PlaylistRule,
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
    ) -> None:
        for name, spec in rule.filters.features.items():
            canonical = self._registry.resolve_name(name)
            if not self._registry.is_known(name):
                errors.append(
                    ValidationIssue(
                        code="UNKNOWN_FILTER",
                        message=f"Unknown feature filter: {name}",
                        path=f"filters.features.{name}",
                    )
                )
                continue
            if self._registry.is_future(canonical):
                warnings.append(
                    ValidationIssue(
                        code="FEATURE_NOT_AVAILABLE_YET",
                        message=f"Feature {name} is not available until phase 7",
                        path=f"filters.features.{name}",
                    )
                )
            if spec.min is not None and spec.max is not None and spec.min > spec.max:
                errors.append(
                    ValidationIssue(
                        code="INVALID_RANGE",
                        message=f"min > max for {name}",
                        path=f"filters.features.{name}",
                    )
                )

    def _validate_weights(
        self,
        rule: PlaylistRule,
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
    ) -> None:
        components = rule.weights.components
        if not components:
            errors.append(
                ValidationIssue(
                    code="NO_SCORING_COMPONENTS",
                    message="At least one scoring component is required",
                    path="weights.components",
                )
            )
            return
        total = sum(c.weight for c in components.values())
        if total <= 0:
            errors.append(
                ValidationIssue(
                    code="NO_SCORING_COMPONENTS",
                    message="Sum of component weights must be > 0",
                    path="weights.components",
                )
            )
        for name, _spec in components.items():
            canonical = self._registry.resolve_name(name)
            if not self._registry.is_known(name):
                errors.append(
                    ValidationIssue(
                        code="UNKNOWN_FILTER",
                        message=f"Unknown scoring component: {name}",
                        path=f"weights.components.{name}",
                    )
                )
            elif self._registry.is_future(canonical):
                warnings.append(
                    ValidationIssue(
                        code="FEATURE_NOT_AVAILABLE_YET",
                        message=f"Scoring component {name} not available until phase 7",
                        path=f"weights.components.{name}",
                    )
                )

    def _validate_ordering(
        self,
        rule: PlaylistRule,
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
    ) -> None:
        mode = rule.ordering.mode
        if mode in FUTURE_ORDERING_MODES:
            errors.append(
                ValidationIssue(
                    code="ORDERING_MODE_NOT_AVAILABLE_YET",
                    message=f"Ordering mode {mode} is not available in phase 5",
                    path="ordering.mode",
                )
            )

    def _validate_sync(
        self,
        rule: PlaylistRule,
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
    ) -> None:
        _ = warnings
        known = {
            "create",
            "replace",
            "add_only",
            "remove_obsolete",
            "replace_after_dry_run",
        }
        if rule.spotify.sync_mode not in known:
            errors.append(
                ValidationIssue(
                    code="UNKNOWN_SYNC_MODE",
                    message=f"Unknown sync mode: {rule.spotify.sync_mode}",
                    path="spotify.sync_mode",
                )
            )

    def _validate_future_fields(
        self,
        rule: PlaylistRule,
        warnings: list[ValidationIssue],
    ) -> None:
        if rule.constraints.cluster_diversity.enabled:
            warnings.append(
                ValidationIssue(
                    code="CLUSTER_SOURCE_NOT_AVAILABLE_YET",
                    message="cluster_diversity is not available until phase 6",
                    path="constraints.cluster_diversity",
                )
            )
        if rule.constraints.vocal_balance.enabled:
            warnings.append(
                ValidationIssue(
                    code="FEATURE_NOT_AVAILABLE_YET",
                    message="vocal_balance is not available until phase 7",
                    path="constraints.vocal_balance",
                )
            )


def parse_rule_json(rule_json: str) -> dict[str, Any]:
    return json.loads(rule_json)
