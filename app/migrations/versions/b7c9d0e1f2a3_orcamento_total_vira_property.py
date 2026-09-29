"""orcamento total vira property (soma dos itens), drop da coluna

A coluna `orcamentos.total` ficou dessincronizada: os itens são lançados pelo
form e nada recalculava a coluna, então orçamentos novos ficavam com `total`
NULL (e o `calc` de agregação do Schema não achava `OrcamentoItem.valor`, que
era campo virtual sem atributo no model). Agora `total` é property
`sum(item.valor)`, como `Pedido` e `Compra` — uma fonte de verdade só.

Revision ID: b7c9d0e1f2a3
Revises: a9f8e7d6c5b4
Create Date: 2026-09-29
"""
from alembic import op
import sqlalchemy as sa

revision = 'b7c9d0e1f2a3'
down_revision = 'a9f8e7d6c5b4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('orcamentos', schema=None) as batch_op:
        batch_op.drop_column('total')


def downgrade():
    with op.batch_alter_table('orcamentos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('total', sa.Numeric(10, 2), nullable=True))
    # Recalcula a partir dos itens para a coluna não voltar zerada.
    op.execute(
        "UPDATE orcamentos SET total = ("
        "  SELECT COALESCE(SUM(i.qtd * i.preco), 0) FROM orcamento_itens i"
        "  WHERE i.orcamento_id = orcamentos.id"
        ")"
    )
