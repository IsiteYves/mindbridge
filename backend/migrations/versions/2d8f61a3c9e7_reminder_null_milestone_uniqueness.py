from alembic import op

revision = "2d8f61a3c9e7"
down_revision = "5e7d0f3a9b14"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "uq_reminder_delivery_no_milestone",
        "reminders",
        ["user_id", "assignment_id", "kind", "offset_days", "fired_for_date"],
        unique=True,
        postgresql_where="milestone_id IS NULL",
    )


def downgrade():
    op.drop_index("uq_reminder_delivery_no_milestone", table_name="reminders")