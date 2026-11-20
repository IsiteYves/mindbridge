"""Add selected_course_ids to lms_integrations, for the persistent Canvas
connection: a later sync re-pulls the courses chosen at connect time without
asking the student to pick them again.

Revision ID: 7a2e4d916b35
Revises: 5e7d0f3a9b14
"""

import sqlalchemy as sa
from alembic import op

revision = "7a2e4d916b35"
down_revision = "5e7d0f3a9b14"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("lms_integrations", sa.Column("selected_course_ids", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("lms_integrations", "selected_course_ids")
