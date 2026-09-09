"""produto: preco->valor + coluna qtd_receita

Revision ID: f9a0b1c2d3e4
Revises: e5f6a7b8c9d0
Create Date: 2026-09-09 00:00:00.000000

Rename a coluna `preco` de `produtos` para `valor` e adiciona a coluna
`qtd_receita`. O preço por unidade passa a ser a prop virtual `preco`
(calc = divide(valor, qtd_minima)) — sem coluna própria.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f9a0b1c2d3e4'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('produtos', 'preco', new_column_name='valor')
    op.add_column('produtos', sa.Column(
        'qtd_receita', sa.Integer(), nullable=False, server_default='1'))


def downgrade():
    op.drop_column('produtos', 'qtd_receita')
    op.alter_column('produtos', 'valor', new_column_name='preco')