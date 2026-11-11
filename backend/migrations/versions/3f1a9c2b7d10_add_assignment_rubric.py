"""Store rubric criteria on assignments

Revision ID: 3f1a9c2b7d10
Revises: db9d7f6bc3c4
Create Date: 2026-11-11 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3f1a9c2b7d10'
down_revision = 'db9d7f6bc3c4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('assignments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('rubric', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('assignments', schema=None) as batch_op:
        batch_op.drop_column('rubric')
