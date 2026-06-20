"""add tipo to ingredients

Revision ID: 31f4e1cd60a4
Revises: 0267716c6c8f
Create Date: 2026-06-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '31f4e1cd60a4'
down_revision = '0267716c6c8f'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('ingredients', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tipo', sa.Integer(), nullable=False, server_default=sa.text('0')))


def downgrade():
    with op.batch_alter_table('ingredients', schema=None) as batch_op:
        batch_op.drop_column('tipo')
