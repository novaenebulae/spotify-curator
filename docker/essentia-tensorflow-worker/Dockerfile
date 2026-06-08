# Essentia *with TensorFlow* worker (phase 6.8B real inference).
#
# Targets:
#   cpu — default local development (python:3.11-slim)
#   gpu — Lambda Labs / NVIDIA Container Toolkit (CUDA runtime)
#
# The upstream ghcr.io/mtg/essentia base image ships an essentia build compiled
# WITHOUT TensorFlow. We use the `essentia-tensorflow` PyPI wheel instead.

# ----- shared application layer ---------------------------------------------

FROM python:3.11-slim AS app-base

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

# essentia-tensorflow is large and worker-only (pinned cp311 manylinux wheel).
RUN uv pip install "essentia-tensorflow==2.1b6.dev1389"

COPY core/app /app/app
COPY core/scripts /app/scripts
COPY core/alembic /app/alembic
COPY core/alembic.ini /app/alembic.ini
COPY scripts/lambda /app/scripts/lambda

# ----- CPU target (local default) -------------------------------------------

FROM app-base AS cpu

CMD ["uv", "run", "python", "scripts/run_essentia_tensorflow_worker.py"]

# ----- GPU target (Lambda / NVIDIA) -------------------------------------------

FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04 AS gpu-base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UV_PYTHON=3.11 \
    UV_PYTHON_PREFERENCE=only-system \
    TF_FORCE_GPU_ALLOW_GROWTH=true \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

# essentia-tensorflow wheels bundle TensorFlow C++ built for CUDA 11.2 / cuDNN 8.1.
# The host driver is newer; conda-forge supplies compatible user-space libs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3.11 \
        python3.11-venv \
        python3-pip \
        ffmpeg \
        curl \
        bzip2 \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.11 /usr/local/bin/python \
    && ln -sf /usr/bin/python3.11 /usr/local/bin/python3 \
    && pip install --no-cache-dir uv \
    && curl -L -o /tmp/Miniforge3.sh \
        "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh" \
    && bash /tmp/Miniforge3.sh -b -p /opt/conda \
    && /opt/conda/bin/conda install -y -c conda-forge cudatoolkit=11.2 cudnn=8.1 \
    && /opt/conda/bin/conda clean -afy \
    && rm -f /tmp/Miniforge3.sh

ENV LD_LIBRARY_PATH=/opt/conda/lib:/usr/local/nvidia/lib:/usr/local/nvidia/lib64

COPY core/pyproject.toml core/uv.lock /app/
RUN uv sync --frozen

RUN uv pip install "essentia-tensorflow==2.1b6.dev1389"

COPY core/app /app/app
COPY core/scripts /app/scripts
COPY core/alembic /app/alembic
COPY core/alembic.ini /app/alembic.ini
COPY scripts/lambda /app/scripts/lambda

FROM gpu-base AS gpu

CMD ["uv", "run", "python", "scripts/run_essentia_tensorflow_worker.py"]
