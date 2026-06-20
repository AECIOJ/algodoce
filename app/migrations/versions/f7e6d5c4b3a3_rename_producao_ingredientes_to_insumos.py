"""rename producao_ingredientes to producao_insumos

Revision ID: fb1c2d3e4f5a
Revises: faeb0c1d2b3a6
Create Date: 2026-06-19 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'fb1c2d3e4f5a'
down_revision = 'faeb0c1d2b3a6'
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table('producao_ingredientes', 'producao_insumos')
    op.alter_column('producao_insumos', 'ingrediente_id', new_column_name='insumo_id')


def downgrade():
    op.alter_column('producao_insumos', 'insumo_id', new_column_name='ingrediente_id')
    op.rename_table('producao_insumos', 'producao_ingredientes')
