# Essentia *with TensorFlow* worker (phase 6.8B real inference).
#
# The upstream ghcr.io/mtg/essentia base image ships an essentia build compiled
# WITHOUT TensorFlow (no TensorflowPredict* algorithms) and for Python 3.9 only,
# which is incompatible with our >=3.11 codebase. Instead we use a plain
# Python 3.11 image and install the `essentia-tensorflow` PyPI wheel, which
# bundles essentia + the TensorflowPredict* algorithms and its own TF runtime.
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UV_PYTHON=3.11 \
    UV_PYTHON_PREFERENCE=only-system

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

COPY core/pyproject.toml core/uv.lock /app/
RUN uv sync --frozen

# essentia-tensorflow is large and worker-only, so it is installed into the uv
# venv here rather than added to the shared lockfile. Pinned to a release that
# publishes a cp311 manylinux wheel (see docs/19).
RUN uv pip install "essentia-tensorflow==2.1b6.dev1389"

COPY core/app /app/app
COPY core/scripts /app/scripts
COPY core/alembic /app/alembic
COPY core/alembic.ini /app/alembic.ini

CMD ["uv", "run", "python", "scripts/run_essentia_tensorflow_worker.py"]
