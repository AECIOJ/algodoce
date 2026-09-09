"""itens: quantidade->qtd, preco_unitario->preco; insumo: unidade_medida->und

Revision ID: 3b7c9d1e5f8a
Revises: f9a0b1c2d3e4
Create Date: 2026-09-09 00:00:01.000000

Renomeia colunas de `orcamento_itens` e `pedido_itens` (`quantidade` ->
`qtd`, `preco_unitario` -> `preco`) e de `insumos` (`unidade_medida` ->
`und`), alinhando os nomes aos das Entities.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '3b7c9d1e5f8a'
down_revision = 'f9a0b1c2d3e4'
branch_labels = None
depends_on = None


def upgrade():
    for table in ('orcamento_itens', 'pedido_itens'):
        op.alter_column(table, 'quantidade', new_column_name='qtd')
        op.alter_column(table, 'preco_unitario', new_column_name='preco')
    op.alter_column('insumos', 'unidade_medida', new_column_name='und')


def downgrade():
    op.alter_column('insumos', 'und', new_column_name='unidade_medida')
    for table in ('orcamento_itens', 'pedido_itens'):
        op.alter_column(table, 'preco', new_column_name='preco_unitario')
        op.alter_column(table, 'qtd', new_column_name='quantidade')