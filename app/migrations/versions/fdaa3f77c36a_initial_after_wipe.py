"""initial after wipe

Revision ID: fdaa3f77c36a
Revises: 
Create Date: 2026-06-23 16:43:33.767680

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fdaa3f77c36a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # --- tabelas sem FK circular ---
    op.create_table('producao',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('descricao', sa.String(length=200), nullable=False),
        sa.Column('data_fim', sa.DateTime(), nullable=True),
        sa.Column('status', sa.Integer(), nullable=False),
        sa.Column('previsao_de', sa.Date(), nullable=True),
        sa.Column('previsao_ate', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('data_pedido', sa.DateTime(), nullable=False),
        sa.Column('data_previsao_entrega', sa.DateTime(), nullable=True),
        sa.Column('data_entrega', sa.DateTime(), nullable=True),
        sa.Column('status', sa.Integer(), nullable=False),
        sa.Column('observacao', sa.Text(), nullable=True),
        sa.Column('total', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('forma_pagamento', sa.Integer(), nullable=False),
        sa.Column('forminhas', sa.Integer(), nullable=False),
        sa.Column('producao_id', sa.Integer(), nullable=True),
        sa.Column('quote_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['conta.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('quotes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('data_pedido', sa.DateTime(), nullable=False),
        sa.Column('cliente_nome', sa.String(length=100), nullable=False),
        sa.Column('cliente_telefone', sa.String(length=20), nullable=False),
        sa.Column('status', sa.Integer(), nullable=False),
        sa.Column('pedido_id', sa.Integer(), nullable=True),
        sa.Column('total', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('observacao', sa.Text(), nullable=True),
        sa.Column('validade', sa.Integer(), nullable=False),
        sa.Column('forma_pagamento', sa.Integer(), nullable=False),
        sa.Column('data_renovacao', sa.DateTime(), nullable=True),
        sa.Column('forminhas', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # --- FKs circulares (precisam de ambas as tabelas existentes) ---
    op.execute('ALTER TABLE orders ADD CONSTRAINT fk_orders_producao '
               'FOREIGN KEY (producao_id) REFERENCES producao (id)')
    op.execute('ALTER TABLE orders ADD CONSTRAINT fk_orders_quotes '
               'FOREIGN KEY (quote_id) REFERENCES quotes (id)')
    op.execute('ALTER TABLE quotes ADD CONSTRAINT fk_quotes_orders '
               'FOREIGN KEY (pedido_id) REFERENCES orders (id)')

    # --- demais tabelas ---
    op.create_table('compras',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('data', sa.Date(), nullable=False),
        sa.Column('fornecedor_id', sa.Integer(), nullable=True),
        sa.Column('valor', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('historico', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['fornecedor_id'], ['conta.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quote_id', sa.Integer(), nullable=True),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('tipo', sa.String(length=30), nullable=True),
        sa.Column('tema', sa.String(length=200), nullable=True),
        sa.Column('obs', sa.Text(), nullable=True),
        sa.Column('data', sa.Date(), nullable=True),
        sa.Column('hora', sa.Time(), nullable=True),
        sa.Column('local', sa.String(length=200), nullable=True),
        sa.Column('convidados', sa.Integer(), nullable=True),
        sa.Column('cerimonial', sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id'),
        sa.UniqueConstraint('quote_id')
    )
    op.create_table('producao_insumos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('producao_id', sa.Integer(), nullable=False),
        sa.Column('insumo_id', sa.Integer(), nullable=False),
        sa.Column('quantidade', sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column('comprado', sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column('unidade', sa.String(length=20), nullable=False),
        sa.Column('tipo', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['insumo_id'], ['ingredients.id'], ),
        sa.ForeignKeyConstraint(['producao_id'], ['producao.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('compra_itens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('compra_id', sa.Integer(), nullable=False),
        sa.Column('insumo_id', sa.Integer(), nullable=False),
        sa.Column('quantidade', sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column('preco', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['compra_id'], ['compras.id'], ),
        sa.ForeignKeyConstraint(['insumo_id'], ['ingredients.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('order_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantidade', sa.Integer(), nullable=False),
        sa.Column('preco_unitario', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('observacao', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('producao_produtos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('producao_id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantidade', sa.Integer(), nullable=False),
        sa.Column('producao_0', sa.Integer(), nullable=False),
        sa.Column('producao_1', sa.Integer(), nullable=False),
        sa.Column('producao_2', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.ForeignKeyConstraint(['producao_id'], ['producao.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('quote_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quote_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantidade', sa.Integer(), nullable=False),
        sa.Column('preco_unitario', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('observacao', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('transacao',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('data', sa.Date(), nullable=False),
        sa.Column('tipo', sa.String(length=1), nullable=False),
        sa.Column('conta_id', sa.Integer(), nullable=True),
        sa.Column('rubrica_id', sa.Integer(), nullable=True),
        sa.Column('fatura', sa.String(length=50), nullable=True),
        sa.Column('valor', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('historico', sa.Text(), nullable=True),
        sa.Column('cancelado', sa.Date(), nullable=True),
        sa.Column('compra_id', sa.Integer(), nullable=True),
        sa.Column('pedido_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['compra_id'], ['compras.id'], ),
        sa.ForeignKeyConstraint(['conta_id'], ['conta.id'], ),
        sa.ForeignKeyConstraint(['pedido_id'], ['orders.id'], ),
        sa.ForeignKeyConstraint(['rubrica_id'], ['rubrica.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('compra_id'),
        sa.UniqueConstraint('pedido_id')
    )
    op.create_table('previsao',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transacao_id', sa.Integer(), nullable=False),
        sa.Column('documento', sa.String(length=50), nullable=True),
        sa.Column('vencimento', sa.Date(), nullable=False),
        sa.Column('previsto', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('realizado', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('variacao', sa.Numeric(precision=12, scale=2), server_default='0', nullable=True),
        sa.ForeignKeyConstraint(['transacao_id'], ['transacao.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('movto',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('data', sa.Date(), nullable=False),
        sa.Column('recurso_id', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(length=1), nullable=False),
        sa.Column('conta_id', sa.Integer(), nullable=True),
        sa.Column('previsao_id', sa.Integer(), nullable=True),
        sa.Column('documento', sa.String(length=50), nullable=True),
        sa.Column('valor', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('variacao', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('sincronizar', sa.Boolean(), nullable=False),
        sa.Column('rubrica_id', sa.Integer(), nullable=True),
        sa.Column('historico', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['conta_id'], ['conta.id'], ),
        sa.ForeignKeyConstraint(['previsao_id'], ['previsao.id'], ),
        sa.ForeignKeyConstraint(['recurso_id'], ['recurso.id'], ),
        sa.ForeignKeyConstraint(['rubrica_id'], ['rubrica.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('movto')
    op.drop_table('previsao')
    op.drop_table('transacao')
    op.drop_table('quote_items')
    op.drop_table('producao_produtos')
    op.drop_table('order_items')
    op.drop_table('compra_itens')
    op.drop_table('producao_insumos')
    op.drop_table('events')
    op.drop_table('compras')
    op.drop_table('quotes')
    op.drop_table('producao')
    op.drop_table('orders')
