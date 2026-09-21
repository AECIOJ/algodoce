"""transacao: prazo/variacao/saldo fisicos; valor = soma das previsoes

Revision ID: b0a1c2d3e4f5
Revises: f3e2d1c0b9a8
Create Date: 2026-09-21

Fundir `total_previsto` -> `valor`: o `valor` passa a ser a soma de
`Previsao.previsto` (como no Pedido, `valor` = soma dos itens); o `valor`
avulso editável é removido. Ainda adiciona os agregados físicos:
`prazo` (resumo dos vencimentos, ex. "30/60/90"), `variacao`
(Σ previsao.variacao) e `saldo` (Σ previsto+variacao-realizado).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b0a1c2d3e4f5'
down_revision = 'f3e2d1c0b9a8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('transacao', schema=None) as batch_op:
        batch_op.add_column(sa.Column('prazo', sa.String(50), server_default='', nullable=False))
        batch_op.add_column(sa.Column('variacao', sa.Numeric(12, 2), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('saldo', sa.Numeric(12, 2), server_default='0', nullable=False))
        batch_op.drop_column('valor')
        batch_op.alter_column('total_previsto', new_column_name='valor')

    # Backfill: prazo = dias até cada vencimento (ex. "0/30/90"); valor = Σ previsto;
    # variacao = Σ variacao; saldo = Σ (previsto + variacao - realizado).
    op.execute("""
        UPDATE transacao t SET
            prazo = COALESCE((
                SELECT string_agg(pd.days::text, '/' ORDER BY pd.venc, pd.pid)
                  FROM (
                      SELECT p.id AS pid, p.vencimento AS venc,
                             (p.vencimento - t.data) AS days
                        FROM previsao p
                       WHERE p.transacao_id = t.id
                  ) pd
            ), ''),
            valor = COALESCE((
                SELECT SUM(p.previsto) FROM previsao p WHERE p.transacao_id = t.id
            ), 0),
            variacao = COALESCE((
                SELECT SUM(COALESCE(p.variacao, 0)) FROM previsao p WHERE p.transacao_id = t.id
            ), 0),
            saldo = COALESCE((
                SELECT SUM(p.previsto + COALESCE(p.variacao, 0)
                           - COALESCE(p.realizado, 0))
                  FROM previsao p WHERE p.transacao_id = t.id
            ), 0)
    """)


def downgrade():
    with op.batch_alter_table('transacao', schema=None) as batch_op:
        batch_op.add_column(sa.Column('valor_avulso', sa.Numeric(12, 2),
                                      server_default='0', nullable=False))
        batch_op.alter_column('valor', new_column_name='total_previsto')

    op.execute("UPDATE transacao SET valor_avulso = COALESCE(total_previsto, 0)")

    with op.batch_alter_table('transacao', schema=None) as batch_op:
        batch_op.alter_column('valor_avulso', new_column_name='valor')
        batch_op.drop_column('saldo')
        batch_op.drop_column('variacao')
        batch_op.drop_column('prazo')