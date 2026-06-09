FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl ca-certificates unzip \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv "yt-dlp[default]" \
    && curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh \
    && deno --version

COPY core/pyproject.toml core/uv.lock /app/
RUN uv sync --frozen

COPY core/app /app/app
COPY core/scripts /app/scripts
COPY core/alembic /app/alembic
COPY core/alembic.ini /app/alembic.ini
COPY profiles /app/profiles

CMD ["uv", "run", "python", "scripts/run_audio_downloader_worker.py"]
