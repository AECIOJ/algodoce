"""add previsao_de and previsao_ate to producao

Revision ID: a8b9c0d1e2f3
Revises: f7e6d5c4b3a4
Create Date: 2026-06-18 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a8b9c0d1e2f3'
down_revision = 'f7e6d5c4b3a4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('producao', schema=None) as batch_op:
        batch_op.add_column(sa.Column('previsao_de', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('previsao_ate', sa.Date(), nullable=True))


def downgrade():
    with op.batch_alter_table('producao', schema=None) as batch_op:
        batch_op.drop_column('previsao_ate')
        batch_op.drop_column('previsao_de')
