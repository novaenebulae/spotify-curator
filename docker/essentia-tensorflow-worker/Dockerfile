# Base image v1; custom spotify-curator-essentia-tensorflow image planned for real TF inference (6.6+).
FROM ghcr.io/mtg/essentia:bullseye-v2.1_beta5

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip curl ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --no-cache-dir uv \
    && ln -sf /usr/bin/python3 /usr/local/bin/python

COPY core/pyproject.toml core/uv.lock /app/
RUN uv sync --frozen

COPY core/app /app/app
COPY core/scripts /app/scripts
COPY core/alembic /app/alembic
COPY core/alembic.ini /app/alembic.ini

CMD ["uv", "run", "python", "scripts/run_essentia_tensorflow_worker.py"]
