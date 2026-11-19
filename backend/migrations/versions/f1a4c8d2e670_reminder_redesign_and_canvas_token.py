import sqlalchemy as sa
from alembic import op

revision = "f1a4c8d2e670"
down_revision = "c4b7e2a91f58"
branch_labels = None
depends_on = None


def upgrade():
    # The old table carries no data worth migrating so it is dropped and recreated rather than being altered column by column.
    op.drop_table("reminders")

    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("milestone_id", sa.Integer(), sa.ForeignKey("milestones.id", ondelete="CASCADE"), nullable=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("offset_days", sa.Integer(), nullable=True),
        sa.Column("fired_for_date", sa.Date(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "user_id", "assignment_id", "milestone_id", "kind", "offset_days", "fired_for_date",
            name="uq_reminder_delivery",
        ),
    )
    op.create_index("ix_reminders_user_id", "reminders", ["user_id"])
    op.create_index("ix_reminders_assignment_id", "reminders", ["assignment_id"])
    op.create_index("ix_reminders_milestone_id", "reminders", ["milestone_id"])

    op.create_table(
        "reminder_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("offset_days", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "offset_days", name="uq_reminder_pref_user_offset"),
    )
    op.create_index("ix_reminder_preferences_user_id", "reminder_preferences", ["user_id"])

    op.add_column("lms_integrations", sa.Column("access_token_encrypted", sa.String(length=1024), nullable=True))


def downgrade():
    op.drop_column("lms_integrations", "access_token_encrypted")

    op.drop_index("ix_reminder_preferences_user_id", table_name="reminder_preferences")
    op.drop_table("reminder_preferences")

    op.drop_index("ix_reminders_milestone_id", table_name="reminders")
    op.drop_index("ix_reminders_assignment_id", table_name="reminders")
    op.drop_index("ix_reminders_user_id", table_name="reminders")
    op.drop_table("reminders")

    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "study_session_id", sa.Integer(), sa.ForeignKey("study_sessions.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("remind_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_reminders_user_id", "reminders", ["user_id"])
    op.create_index("ix_reminders_study_session_id", "reminders", ["study_session_id"])