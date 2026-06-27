"""comercial_reforma

Revision ID: d5ff48124a39
Revises: 4e3611b85f3f
Create Date: 2026-06-26 17:42:08.713342

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5ff48124a39'
down_revision = '4e3611b85f3f'
branch_labels = None
depends_on = None


def upgrade():
    # --- forma_pagamento table ---
    op.create_table('forma_pagamento',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=50), nullable=False),
        sa.Column('uso', sa.Integer(), nullable=False),
        sa.Column('modo', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # seed forma_pagamento
    op.execute(
        "INSERT INTO forma_pagamento (id, nome, uso, modo) VALUES "
        "(1, 'Dinheiro', 1, 0),"
        "(2, 'Pix', 1, 0),"
        "(3, 'Cartão Débito', 1, 0),"
        "(4, 'Cartão Crédito', 1, 1),"
        "(5, 'Boleto', 2, 1),"
        "(6, 'Depósito', 1, 0)"
    )
    op.execute("SELECT setval('forma_pagamento_id_seq', 6)")

    # --- compras ---
    op.add_column('compras', sa.Column('data_recepcao', sa.Date(), nullable=True))
    op.add_column('compras', sa.Column('forma_pagamento_id', sa.Integer(), nullable=True))
    op.add_column('compras', sa.Column('transacao_id', sa.Integer(), nullable=True))
    op.add_column('compras', sa.Column('movto_id', sa.Integer(), nullable=True))
    op.add_column('compras', sa.Column('status', sa.Integer(), nullable=True))
    op.execute("UPDATE compras SET status = 1")
    op.alter_column('compras', 'status', nullable=False, server_default=sa.text('0'))

    op.create_unique_constraint(None, 'compras', ['transacao_id'])
    op.create_unique_constraint(None, 'compras', ['movto_id'])
    op.create_foreign_key(None, 'compras', 'movto', ['movto_id'], ['id'])
    op.create_foreign_key(None, 'compras', 'transacao', ['transacao_id'], ['id'])
    op.create_foreign_key(None, 'compras', 'forma_pagamento', ['forma_pagamento_id'], ['id'])

    # --- orders ---
    op.add_column('orders', sa.Column('forma_pagamento_id', sa.Integer(), nullable=True))
    op.add_column('orders', sa.Column('transacao_id', sa.Integer(), nullable=True))
    op.add_column('orders', sa.Column('movto_id', sa.Integer(), nullable=True))
    op.create_unique_constraint(None, 'orders', ['transacao_id'])
    op.create_unique_constraint(None, 'orders', ['movto_id'])
    op.create_foreign_key(None, 'orders', 'forma_pagamento', ['forma_pagamento_id'], ['id'])
    op.create_foreign_key(None, 'orders', 'transacao', ['transacao_id'], ['id'])
    op.create_foreign_key(None, 'orders', 'movto', ['movto_id'], ['id'])

    op.execute("UPDATE orders SET forma_pagamento_id = 1 WHERE forma_pagamento = 0")
    op.execute("UPDATE orders SET forma_pagamento_id = 4 WHERE forma_pagamento = 1")
    op.execute("UPDATE orders SET forma_pagamento_id = 1 WHERE forma_pagamento = 2")

    op.execute("UPDATE orders SET status = 8 WHERE status = 3")

    # --- quotes ---
    op.add_column('quotes', sa.Column('forma_pagamento_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'quotes', 'forma_pagamento', ['forma_pagamento_id'], ['id'])

    op.execute("UPDATE quotes SET forma_pagamento_id = 1 WHERE forma_pagamento = 0")
    op.execute("UPDATE quotes SET forma_pagamento_id = 4 WHERE forma_pagamento = 1")
    op.execute("UPDATE quotes SET forma_pagamento_id = 1 WHERE forma_pagamento = 2")

    # --- transacao -> compra/order links ---
    op.execute("UPDATE compras SET transacao_id = transacao.id FROM transacao WHERE transacao.compra_id = compras.id")
    op.execute("UPDATE orders SET transacao_id = transacao.id FROM transacao WHERE transacao.pedido_id = orders.id")

    with op.batch_alter_table('transacao', schema=None) as batch_op:
        batch_op.drop_constraint('transacao_compra_id_key', type_='unique')
        batch_op.drop_constraint('transacao_pedido_id_key', type_='unique')
        batch_op.drop_constraint('transacao_pedido_id_fkey', type_='foreignkey')
        batch_op.drop_constraint('transacao_compra_id_fkey', type_='foreignkey')
        batch_op.drop_column('compra_id')
        batch_op.drop_column('pedido_id')


def downgrade():
    with op.batch_alter_table('transacao', schema=None) as batch_op:
        batch_op.add_column(sa.Column('pedido_id', sa.INTEGER(), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('compra_id', sa.INTEGER(), autoincrement=False, nullable=True))
        batch_op.create_foreign_key('transacao_compra_id_fkey', 'compras', ['compra_id'], ['id'])
        batch_op.create_foreign_key('transacao_pedido_id_fkey', 'orders', ['pedido_id'], ['id'])
        batch_op.create_unique_constraint('transacao_pedido_id_key', ['pedido_id'])
        batch_op.create_unique_constraint('transacao_compra_id_key', ['compra_id'])

    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('forma_pagamento_id')

    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint(None, type_='unique')
        batch_op.drop_constraint(None, type_='unique')
        batch_op.drop_column('movto_id')
        batch_op.drop_column('transacao_id')
        batch_op.drop_column('forma_pagamento_id')
        batch_op.execute("UPDATE orders SET status = 3 WHERE status = 8")

    with op.batch_alter_table('compras', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint(None, type_='unique')
        batch_op.drop_constraint(None, type_='unique')
        batch_op.drop_column('movto_id')
        batch_op.drop_column('transacao_id')
        batch_op.drop_column('forma_pagamento_id')
        batch_op.drop_column('data_recepcao')
        batch_op.drop_column('status')

    op.drop_table('forma_pagamento')
