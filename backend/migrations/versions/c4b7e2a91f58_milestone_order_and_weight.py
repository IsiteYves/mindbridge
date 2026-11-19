"""Add explicit ordering and rubric weight to milestones.

Revision ID: c4b7e2a91f58
Revises: a8e1c3d5f7b9
"""

import sqlalchemy as sa
from alembic import op

revision = "c4b7e2a91f58"
down_revision = "a8e1c3d5f7b9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("milestones", sa.Column("position", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("milestones", sa.Column("weight", sa.Integer(), nullable=True))

    # Backfill: number each assignment's milestones from 0 in target-date order,
    # which is the order they were displayed in before this migration.
    op.execute(
        """
        UPDATE milestones AS m
        SET position = ordered.row_number - 1
        FROM (
            SELECT id,
                   ROW_NUMBER() OVER (PARTITION BY assignment_id ORDER BY target_date, id) AS row_number
            FROM milestones
        ) AS ordered
        WHERE m.id = ordered.id
        """
    )

    op.create_index("ix_milestones_assignment_position", "milestones", ["assignment_id", "position"])
    op.create_check_constraint(
        "ck_milestones_weight_range",
        "milestones",
        "weight IS NULL OR (weight >= 0 AND weight <= 100)",
    )


def downgrade():
    op.drop_constraint("ck_milestones_weight_range", "milestones", type_="check")
    op.drop_index("ix_milestones_assignment_position", table_name="milestones")
    op.drop_column("milestones", "weight")
    op.drop_column("milestones", "position")
