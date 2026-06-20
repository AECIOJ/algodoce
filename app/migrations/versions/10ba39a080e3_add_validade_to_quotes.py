"""add validade to quotes

Revision ID: 10ba39a080e3
Revises: 31f4e1cd60a4
Create Date: 2026-06-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '10ba39a080e3'
down_revision = '31f4e1cd60a4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('validade', sa.Integer(), nullable=False, server_default=sa.text('3')))


def downgrade():
    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.drop_column('validade')
