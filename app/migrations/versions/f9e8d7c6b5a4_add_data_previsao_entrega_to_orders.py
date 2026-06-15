"""add data_previsao_entrega to orders

Revision ID: f9e8d7c6b5a4
Revises: b4c3a1d9e8f7
Create Date: 2026-06-14 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'f9e8d7c6b5a4'
down_revision = 'b4c3a1d9e8f7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('data_previsao_entrega', sa.Date(), nullable=True))


def downgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('data_previsao_entrega')
