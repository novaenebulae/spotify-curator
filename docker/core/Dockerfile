FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY core/pyproject.toml core/uv.lock /app/

RUN pip install --no-cache-dir uv \
    && uv sync --frozen

COPY core/app /app/app
COPY core/scripts /app/scripts
COPY core/alembic /app/alembic
COPY core/alembic.ini /app/alembic.ini
COPY profiles /app/profiles

EXPOSE 8765

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8765", "--log-level", "info", "--access-log"]

