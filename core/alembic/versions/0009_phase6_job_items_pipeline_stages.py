"""Phase 6 pipeline stages on job_items.

Revision ID: 0009_phase6_job_items_pipeline_stages
Revises: 0008_phase5_playlist_engine
Create Date: 2026-06-03

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_phase6_job_items_pipeline_stages"
down_revision: str | None = "0008_phase5_playlist_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("job_items", schema=None) as batch_op:
        batch_op.add_column(sa.Column("stage_name", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("depends_on_item_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("consumer_group", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("model_name", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("pipeline_version", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("blocked_reason", sa.String(length=512), nullable=True))
        batch_op.create_foreign_key(
            "fk_job_items_depends_on_item_id",
            "job_items",
            ["depends_on_item_id"],
            ["id"],
        )
        batch_op.create_index("ix_job_items_stage_name", ["stage_name"], unique=False)
        batch_op.create_index(
            "ix_job_items_job_stage_status",
            ["job_id", "stage_name", "status"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("job_items", schema=None) as batch_op:
        batch_op.drop_index("ix_job_items_job_stage_status")
        batch_op.drop_index("ix_job_items_stage_name")
        batch_op.drop_constraint("fk_job_items_depends_on_item_id", type_="foreignkey")
        batch_op.drop_column("blocked_reason")
        batch_op.drop_column("pipeline_version")
        batch_op.drop_column("model_name")
        batch_op.drop_column("consumer_group")
        batch_op.drop_column("depends_on_item_id")
        batch_op.drop_column("stage_name")
