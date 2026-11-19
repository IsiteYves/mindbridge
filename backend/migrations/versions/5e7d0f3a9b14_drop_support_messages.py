"""Drop support_messages.

Revision ID: 5e7d0f3a9b14
Revises: 9b3e6a1d4c82
"""

import sqlalchemy as sa
from alembic import op

revision = "5e7d0f3a9b14"
down_revision = "9b3e6a1d4c82"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("support_messages")


def downgrade():
    op.create_table(
        "support_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("message", sa.String(length=2000), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="new"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
