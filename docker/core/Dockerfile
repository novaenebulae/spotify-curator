FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY core/pyproject.toml core/uv.lock /app/

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates unzip \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv "yt-dlp[default]" \
    && curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh \
    && uv sync --frozen

COPY core/app /app/app
COPY core/scripts /app/scripts
COPY core/alembic /app/alembic
COPY core/alembic.ini /app/alembic.ini
COPY profiles /app/profiles

EXPOSE 8765

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8765", "--log-level", "info", "--access-log"]

