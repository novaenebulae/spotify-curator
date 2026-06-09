#!/usr/bin/env python3
"""Batch copy SQLite runtime DB into PostgreSQL (pgloader fallback for large DBs)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import BigInteger, Integer, MetaData, create_engine, inspect, text


def copy_database(*, sqlite_url: str, postgres_url: str, batch_size: int = 2000) -> None:
    src = create_engine(sqlite_url, future=True)
    dst = create_engine(postgres_url, future=True)

    src_meta = MetaData()
    src_meta.reflect(bind=src)
    dst_meta = MetaData()
    dst_meta.reflect(bind=dst)

    if not dst_meta.tables:
        raise RuntimeError(
            "Postgres schema is empty. Run: docker compose ... run core-api uv run alembic upgrade head"
        )

    with dst.connect() as conn:
        if conn.dialect.name == "postgresql":
            table_list = ", ".join(f'"{name}"' for name in dst_meta.tables)
            conn.execute(text(f"TRUNCATE {table_list} RESTART IDENTITY CASCADE"))
            conn.execute(text("SET session_replication_role = replica"))
            conn.commit()

    table_names = [name for name in src_meta.tables if name in dst_meta.tables]
    table_names.sort(key=lambda n: (0 if n == "alembic_version" else 1, n))

    with src.connect() as src_conn, dst.connect() as dst_conn:
        for table_name in table_names:
            if table_name == "alembic_version":
                continue
            src_table = src_meta.tables[table_name]
            dst_table = dst_meta.tables[table_name]
            rows = src_conn.execute(src_table.select()).mappings().all()
            if not rows:
                print(f"{table_name}: 0 rows")
                continue
            inserted = 0
            for offset in range(0, len(rows), batch_size):
                chunk = rows[offset : offset + batch_size]
                dst_conn.execute(dst_table.insert(), chunk)
                inserted += len(chunk)
            dst_conn.commit()
            print(f"{table_name}: {inserted} rows")

        if dst_conn.dialect.name == "postgresql":
            dst_conn.execute(text("SET session_replication_role = DEFAULT"))
            for table_name, table in dst_meta.tables.items():
                if "id" not in table.c:
                    continue
                id_type = table.c.id.type
                if not isinstance(id_type, (Integer, BigInteger)):
                    continue
                dst_conn.execute(
                    text(
                        f"""
                        SELECT setval(
                            pg_get_serial_sequence('"{table_name}"', 'id'),
                            GREATEST(COALESCE((SELECT MAX(id) FROM "{table_name}"), 0), 1)
                        )
                        WHERE pg_get_serial_sequence('"{table_name}"', 'id') IS NOT NULL
                        """
                    )
                )
            dst_conn.commit()
        version = src_conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        if version:
            dst_conn.execute(text("DELETE FROM alembic_version"))
            dst_conn.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:v)"),
                {"v": version},
            )
            dst_conn.commit()
            print(f"alembic_version: {version}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Copy SQLite DB to PostgreSQL in batches")
    parser.add_argument(
        "--sqlite-url",
        default=f"sqlite:///{Path('/home/ubuntu/spotify-curator-runtime/data/spotify_curator.sqlite')}",
    )
    parser.add_argument(
        "--postgres-url",
        default="postgresql+psycopg://spotify:spotify@127.0.0.1:5432/spotify_curator",
    )
    parser.add_argument("--batch-size", type=int, default=2000)
    args = parser.parse_args()
    try:
        copy_database(
            sqlite_url=args.sqlite_url,
            postgres_url=args.postgres_url,
            batch_size=args.batch_size,
        )
        return 0
    except Exception as exc:
        print(f"copy failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
