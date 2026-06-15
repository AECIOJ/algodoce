"""change data_entrega and data_previsao_entrega to DateTime

Revision ID: a2b3c4d5e6f7
Revises: f9e8d7c6b5a4
Create Date: 2026-06-14 11:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'a2b3c4d5e6f7'
down_revision = 'f9e8d7c6b5a4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.alter_column('data_entrega', type_=sa.DateTime(), existing_type_=sa.Date())
        batch_op.alter_column('data_previsao_entrega', type_=sa.DateTime(), existing_type_=sa.Date())


def downgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.alter_column('data_entrega', type_=sa.Date(), existing_type_=sa.DateTime())
        batch_op.alter_column('data_previsao_entrega', type_=sa.Date(), existing_type_=sa.DateTime())
