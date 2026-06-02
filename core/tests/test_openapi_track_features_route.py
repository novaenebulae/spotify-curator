from __future__ import annotations

from app.main import create_app


def test_openapi_includes_track_features_route() -> None:
    schema = create_app().openapi()
    paths = schema.get("paths", {})
    assert "/api/v1/features/tracks/{track_id}" in paths
    get_op = paths["/api/v1/features/tracks/{track_id}"].get("get", {})
    assert get_op.get("operationId") or get_op.get("summary") or get_op.get("tags")
