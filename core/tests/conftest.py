import os
import sys
from pathlib import Path

import pytest

CORE_ROOT = Path(__file__).resolve().parents[1]

if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

os.environ.setdefault("PYTHONPATH", str(CORE_ROOT))


@pytest.fixture(autouse=True)
def _reset_sqlite_engine() -> None:
    from app.database.engine import reset_engine

    reset_engine()
    yield
    reset_engine()
