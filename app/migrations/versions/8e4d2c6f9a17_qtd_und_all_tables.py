"""quantidade -> qtd; unidade -> und em todas as tabelas

Revision ID: 8e4d2c6f9a17
Revises: 3b7c9d1e5f8a
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa

revision = '8e4d2c6f9a17'
down_revision = '3b7c9d1e5f8a'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('compra_itens', 'quantidade', new_column_name='qtd')
    op.alter_column('producao_insumos', 'quantidade', new_column_name='qtd')
    op.alter_column('producao_insumos', 'unidade', new_column_name='und')
    op.alter_column('producao_produtos', 'quantidade', new_column_name='qtd')
    op.alter_column('produto_insumos', 'quantidade', new_column_name='qtd')
    op.alter_column('produto_insumos', 'unidade', new_column_name='und')
    op.alter_column('insumo_conversoes', 'unidade', new_column_name='und')


def downgrade():
    op.alter_column('compra_itens', 'qtd', new_column_name='quantidade')
    op.alter_column('producao_insumos', 'qtd', new_column_name='quantidade')
    op.alter_column('producao_insumos', 'und', new_column_name='unidade')
    op.alter_column('producao_produtos', 'qtd', new_column_name='quantidade')
    op.alter_column('produto_insumos', 'qtd', new_column_name='quantidade')
    op.alter_column('produto_insumos', 'und', new_column_name='unidade')
    op.alter_column('insumo_conversoes', 'und', new_column_name='unidade')