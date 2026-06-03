from pathlib import Path


def test_alembic_ini_has_no_driver_placeholder() -> None:
    """Regression: template driver:// breaks `uv run alembic upgrade head` on host."""
    ini = (Path(__file__).resolve().parents[1] / "alembic.ini").read_text(encoding="utf-8")
    assert "driver://user:pass@localhost/dbname" not in ini
