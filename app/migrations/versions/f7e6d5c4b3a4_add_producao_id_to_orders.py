"""add producao_id to orders

Revision ID: f7e6d5c4b3a4
Revises: f7e6d5c4b3a3
Create Date: 2026-06-18 10:03:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'f7e6d5c4b3a4'
down_revision = 'f7e6d5c4b3a3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('producao_id', sa.Integer(), sa.ForeignKey('producao.id'), nullable=True))


def downgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('producao_id')
