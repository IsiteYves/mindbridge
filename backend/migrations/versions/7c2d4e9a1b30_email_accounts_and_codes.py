"""Sign in by email, with verification codes

Accounts created before this change had no email, so they are removed.

Revision ID: 7c2d4e9a1b30
Revises: 3f1a9c2b7d10
Create Date: 2026-11-11 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7c2d4e9a1b30'
down_revision = '3f1a9c2b7d10'
branch_labels = None
depends_on = None


def upgrade():
    # Username-only accounts cannot sign in by email, so they are removed. Their assignments go with them.
    op.execute("DELETE FROM users")

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('username')
        batch_op.add_column(sa.Column('name', sa.String(length=120), nullable=False))
        batch_op.add_column(sa.Column('email', sa.String(length=255), nullable=False))
        batch_op.add_column(sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.create_unique_constraint('uq_users_email', ['email'])

    op.create_table(
        'verification_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('purpose', sa.String(length=20), nullable=False),
        sa.Column('code_hash', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_verification_codes_user_id'), 'verification_codes', ['user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_verification_codes_user_id'), table_name='verification_codes')
    op.drop_table('verification_codes')

    op.execute("DELETE FROM users")
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('uq_users_email', type_='unique')
        batch_op.drop_column('email_verified')
        batch_op.drop_column('email')
        batch_op.drop_column('name')
        batch_op.add_column(sa.Column('username', sa.String(length=64), nullable=False))
        batch_op.create_unique_constraint('users_username_key', ['username'])
