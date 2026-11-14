"""Add support messages for the internal admin dashboard

Revision ID: a8e1c3d5f7b9
Revises: 7c2d4e9a1b30
Create Date: 2026-11-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a8e1c3d5f7b9'
down_revision = '7c2d4e9a1b30'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'support_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('message', sa.String(length=2000), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='new', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('support_messages')
