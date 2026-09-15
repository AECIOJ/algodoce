"""inverte vínculo financeiro: pedido_id/compra_id em transacao e movimentos

Revision ID: f1a2b3c4d5e6
Revises: e5f7a9b1c3d6
Create Date: 2026-09-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'e5f7a9b1c3d6'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # 1. Add pedido_id / compra_id em transacao (recria colunas históricas removidas na reforma)
    with op.batch_alter_table('transacao') as batch_op:
        batch_op.add_column(sa.Column('pedido_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('compra_id', sa.Integer(), nullable=True))
        batch_op.create_unique_constraint('transacao_pedido_id_key', ['pedido_id'])
        batch_op.create_unique_constraint('transacao_compra_id_key', ['compra_id'])
        batch_op.create_foreign_key('transacao_pedido_id_fkey', 'pedidos', ['pedido_id'], ['id'])
        batch_op.create_foreign_key('transacao_compra_id_fkey', 'compras', ['compra_id'], ['id'])

    # 2. Add pedido_id / compra_id em movimentos
    with op.batch_alter_table('movimentos') as batch_op:
        batch_op.add_column(sa.Column('pedido_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('compra_id', sa.Integer(), nullable=True))
        batch_op.create_unique_constraint('movimentos_pedido_id_key', ['pedido_id'])
        batch_op.create_unique_constraint('movimentos_compra_id_key', ['compra_id'])
        batch_op.create_foreign_key('movimentos_pedido_id_fkey', 'pedidos', ['pedido_id'], ['id'])
        batch_op.create_foreign_key('movimentos_compra_id_fkey', 'compras', ['compra_id'], ['id'])

    # 3. Backfill dos vínculos existentes
    conn.execute(sa.text(
        "UPDATE transacao SET pedido_id = pedidos.id "
        "FROM pedidos WHERE pedidos.transacao_id = transacao.id"))
    conn.execute(sa.text(
        "UPDATE transacao SET compra_id = compras.id "
        "FROM compras WHERE compras.transacao_id = transacao.id"))
    conn.execute(sa.text(
        "UPDATE movimentos SET pedido_id = pedidos.id "
        "FROM pedidos WHERE pedidos.movimento_id = movimentos.id"))
    conn.execute(sa.text(
        "UPDATE movimentos SET compra_id = compras.id "
        "FROM compras WHERE compras.movimento_id = movimentos.id"))

    # 4. Drop colunas antigas de pedidos / compras
    with op.batch_alter_table('pedidos') as batch_op:
        batch_op.drop_column('transacao_id')
        batch_op.drop_column('movimento_id')

    with op.batch_alter_table('compras') as batch_op:
        batch_op.drop_column('transacao_id')
        batch_op.drop_column('movimento_id')


def downgrade():
    conn = op.get_bind()

    # Re-adicionar transacao_id / movimento_id em pedidos
    with op.batch_alter_table('pedidos') as batch_op:
        batch_op.add_column(sa.Column('transacao_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('movimento_id', sa.Integer(), nullable=True))
        batch_op.create_unique_constraint('orders_transacao_id_key', ['transacao_id'])
        batch_op.create_unique_constraint('orders_movto_id_key', ['movimento_id'])
        batch_op.create_foreign_key('pedidos_transacao_id_fkey', 'transacao', ['transacao_id'], ['id'])
        batch_op.create_foreign_key('pedidos_movimento_id_fkey', 'movimentos', ['movimento_id'], ['id'])

    # Re-adicionar em compras
    with op.batch_alter_table('compras') as batch_op:
        batch_op.add_column(sa.Column('transacao_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('movimento_id', sa.Integer(), nullable=True))
        batch_op.create_unique_constraint('compras_transacao_id_key', ['transacao_id'])
        batch_op.create_unique_constraint('compras_movto_id_key', ['movimento_id'])
        batch_op.create_foreign_key('compras_transacao_id_fkey', 'transacao', ['transacao_id'], ['id'])
        batch_op.create_foreign_key('compras_movimento_id_fkey', 'movimentos', ['movimento_id'], ['id'])

    # Backfill reverso
    conn.execute(sa.text(
        "UPDATE pedidos SET transacao_id = transacao.id "
        "FROM transacao WHERE transacao.pedido_id = pedidos.id"))
    conn.execute(sa.text(
        "UPDATE pedidos SET movimento_id = movimentos.id "
        "FROM movimentos WHERE movimentos.pedido_id = pedidos.id"))
    conn.execute(sa.text(
        "UPDATE compras SET transacao_id = transacao.id "
        "FROM transacao WHERE transacao.compra_id = compras.id"))
    conn.execute(sa.text(
        "UPDATE compras SET movimento_id = movimentos.id "
        "FROM movimentos WHERE movimentos.compra_id = compras.id"))

    # Drop novas colunas
    with op.batch_alter_table('movimentos') as batch_op:
        batch_op.drop_column('pedido_id')
        batch_op.drop_column('compra_id')

    with op.batch_alter_table('transacao') as batch_op:
        batch_op.drop_column('pedido_id')
        batch_op.drop_column('compra_id')
