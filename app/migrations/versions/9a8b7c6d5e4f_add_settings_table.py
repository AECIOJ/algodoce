"""add settings table

Revision ID: 9a8b7c6d5e4f
Revises: 57e7adb0ec22
Create Date: 2026-06-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9a8b7c6d5e4f'
down_revision = '57e7adb0ec22'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('encrypted_value', sa.Text(), nullable=False, server_default=''),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key'),
    )


def downgrade():
    op.drop_table('settings')
