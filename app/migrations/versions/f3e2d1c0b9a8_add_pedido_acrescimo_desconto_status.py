"""add pedido valor acrescimo desconto, compra acrescimo desconto, transacao/transferencia status

Revision ID: f3e2d1c0b9a8
Revises: a4b5c6d7e8f9
Create Date: 2026-09-15
"""
from alembic import op
import sqlalchemy as sa

revision = 'f3e2d1c0b9a8'
down_revision = 'a4b5c6d7e8f9'
branch_labels = None
depends_on = None


def upgrade():
    # --- Pedido: add valor/acrescimo/desconto, backfill, drop total ---
    with op.batch_alter_table('pedidos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('valor', sa.Numeric(10, 2), server_default='0', nullable=True))
        batch_op.add_column(sa.Column('acrescimo', sa.Numeric(10, 2), server_default='0', nullable=True))
        batch_op.add_column(sa.Column('desconto', sa.Numeric(10, 2), server_default='0', nullable=True))

    op.execute("UPDATE pedidos SET valor = COALESCE(total, 0)")

    with op.batch_alter_table('pedidos', schema=None) as batch_op:
        batch_op.alter_column('valor', nullable=False, server_default='0')
        batch_op.alter_column('acrescimo', nullable=False, server_default='0')
        batch_op.alter_column('desconto', nullable=False, server_default='0')
        batch_op.drop_column('total')

    # --- Compra: add acrescimo/desconto ---
    with op.batch_alter_table('compras', schema=None) as batch_op:
        batch_op.add_column(sa.Column('acrescimo', sa.Numeric(10, 2), server_default='0', nullable=True))
        batch_op.add_column(sa.Column('desconto', sa.Numeric(10, 2), server_default='0', nullable=True))

    with op.batch_alter_table('compras', schema=None) as batch_op:
        batch_op.alter_column('acrescimo', nullable=False, server_default='0')
        batch_op.alter_column('desconto', nullable=False, server_default='0')

    # --- Transacao: add status column + backfill ---
    with op.batch_alter_table('transacao', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.Integer(), server_default='0', nullable=True))

    op.execute("""
        UPDATE transacao t SET status = CASE
            WHEN t.cancelado IS NOT NULL THEN 8
            WHEN t.total_previsto IS NULL
                 OR t.total_previsto = 0
                 OR ABS(CAST(t.total_previsto AS DOUBLE PRECISION) - CAST(t.valor AS DOUBLE PRECISION)) > 0.005
                 OR NOT EXISTS (SELECT 1 FROM previsao p WHERE p.transacao_id = t.id)
                THEN 0
            ELSE (SELECT MAX(CASE
                WHEN p.realizado IS NULL THEN 1
                WHEN p.realizado >= (p.previsto + COALESCE(p.variacao, 0)) THEN 9
                ELSE 2
            END) FROM previsao p WHERE p.transacao_id = t.id)
        END
    """)

    with op.batch_alter_table('transacao', schema=None) as batch_op:
        batch_op.alter_column('status', nullable=False, server_default='0')

    # --- Transferencia: add status column + backfill ---
    with op.batch_alter_table('transferencias', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(20), server_default='Editando', nullable=True))

    op.execute("""
        UPDATE transferencias SET status = CASE
            WHEN id NOT IN (SELECT DISTINCT transferencia_id FROM movimentos WHERE transferencia_id IS NOT NULL)
                 OR id IS NULL
                THEN 'Editando'
            WHEN ABS(COALESCE(total, 0)) > 0.005
                THEN 'Pendente'
            ELSE 'Fechada'
        END
    """)

    with op.batch_alter_table('transferencias', schema=None) as batch_op:
        batch_op.alter_column('status', nullable=False, server_default='Editando')


def downgrade():
    # Transferencia
    with op.batch_alter_table('transferencias', schema=None) as batch_op:
        batch_op.drop_column('status')

    # Transacao
    with op.batch_alter_table('transacao', schema=None) as batch_op:
        batch_op.drop_column('status')

    # Compra
    with op.batch_alter_table('compras', schema=None) as batch_op:
        batch_op.drop_column('desconto')
        batch_op.drop_column('acrescimo')

    # Pedido
    with op.batch_alter_table('pedidos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('total', sa.Numeric(10, 2), server_default='0', nullable=True))

    op.execute("UPDATE pedidos SET total = COALESCE(valor, 0)")

    with op.batch_alter_table('pedidos', schema=None) as batch_op:
        batch_op.alter_column('total', nullable=False, server_default='0')
        batch_op.drop_column('desconto')
        batch_op.drop_column('acrescimo')
        batch_op.drop_column('valor')
