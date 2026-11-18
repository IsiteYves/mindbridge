"""Add focus_sessions and daily_goals.

Backs the focus timer and the "today" checklist on the student home screen.
Both are new, additive tables; nothing existing changes shape.

Revision ID: 9b3e6a1d4c82
Revises: f1a4c8d2e670
"""

import sqlalchemy as sa
from alembic import op

revision = "9b3e6a1d4c82"
down_revision = "f1a4c8d2e670"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "focus_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        # SET NULL, not CASCADE: deleting a milestone from a plan should not erase
        # focus time the student already logged against it.
        sa.Column("milestone_id", sa.Integer(), sa.ForeignKey("milestones.id", ondelete="SET NULL"), nullable=True),
        sa.Column("planned_minutes", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_focus_sessions_user_id", "focus_sessions", ["user_id"])
    op.create_index("ix_focus_sessions_milestone_id", "focus_sessions", ["milestone_id"])

    op.create_table(
        "daily_goals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("goal_date", sa.Date(), nullable=False),
        sa.Column("target_count", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "goal_date", name="uq_daily_goal_user_date"),
    )
    op.create_index("ix_daily_goals_user_id", "daily_goals", ["user_id"])


def downgrade():
    op.drop_index("ix_daily_goals_user_id", table_name="daily_goals")
    op.drop_table("daily_goals")

    op.drop_index("ix_focus_sessions_milestone_id", table_name="focus_sessions")
    op.drop_index("ix_focus_sessions_user_id", table_name="focus_sessions")
    op.drop_table("focus_sessions")
