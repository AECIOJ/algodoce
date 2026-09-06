"""rename tables/columns to PT

Revision ID: e5f6a7b8c9d0
Revises: a1d2e3f4a5b6
Create Date: 2026-09-06 00:00:00.000000

Tolerante a divergencias de nomes de constraints/sequences entre bancos
(DROP IF EXISTS): o RENAME do Postgres atualiza as dependencias
automaticamente, entao o essencial (tabelas/colunas) sempre aplica.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'e5f6a7b8c9d0'
down_revision = 'a1d2e3f4a5b6'
branch_labels = None
depends_on = None


# (constraint, tabela) — nomes levantados do banco de origem; IF EXISTS
# absorve divergencias em bancos criados por outro historico.
_DROPS = [
    ('compra_itens_insumo_id_fkey', 'compra_itens'),
    ('compras_movto_id_fkey', 'compras'),
    ('events_order_id_fkey', 'events'),
    ('events_quote_id_fkey', 'events'),
    ('movto_conta_id_fkey', 'movto'),
    ('movto_recurso_id_fkey', 'movto'),
    ('movto_previsao_id_fkey', 'movto'),
    ('movto_operacao_id_fkey', 'movto'),
    ('movto_trf_id_fkey', 'movto'),
    ('order_items_order_id_fkey', 'order_items'),
    ('order_items_product_id_fkey', 'order_items'),
    ('fk_orders_producao', 'orders'),
    ('fk_orders_quotes', 'orders'),
    ('orders_carteira_id_fkey', 'orders'),
    ('orders_client_id_fkey', 'orders'),
    ('orders_movto_id_fkey', 'orders'),
    ('orders_transacao_id_fkey', 'orders'),
    ('producao_insumos_insumo_id_fkey', 'producao_insumos'),
    ('producao_produtos_order_id_fkey', 'producao_produtos'),
    ('producao_produtos_product_id_fkey', 'producao_produtos'),
    ('product_ingredients_ingredient_id_fkey', 'product_ingredients'),
    ('product_ingredients_product_id_fkey', 'product_ingredients'),
    ('fk_products_category_id', 'products'),
    ('quote_items_product_id_fkey', 'quote_items'),
    ('quote_items_quote_id_fkey', 'quote_items'),
    ('fk_quotes_orders', 'quotes'),
    ('quotes_carteira_id_fkey', 'quotes'),
    ('unit_conversions_ingredient_id_fkey', 'unit_conversions'),
]

# (tabela_antiga, tabela_nova)
_TABLES = [
    ('categories', 'categorias'),
    ('events', 'eventos'),
    ('ingredients', 'insumos'),
    ('movto', 'movimentos'),
    ('order_items', 'pedido_itens'),
    ('orders', 'pedidos'),
    ('product_ingredients', 'produto_insumos'),
    ('products', 'produtos'),
    ('quote_items', 'orcamento_itens'),
    ('quotes', 'orcamentos'),
    ('recurso_trf', 'transferencias'),
    ('settings', 'configuracoes'),
    ('unit_conversions', 'insumo_conversoes'),
    ('users', 'usuarios'),
]

# (tabela_nova, coluna_antiga, coluna_nova)
_COLUMNS = [
    ('pedidos', 'client_id', 'conta_id'),
    ('pedidos', 'movto_id', 'movimento_id'),
    ('pedidos', 'quote_id', 'orcamento_id'),
    ('pedido_itens', 'order_id', 'pedido_id'),
    ('pedido_itens', 'product_id', 'produto_id'),
    ('orcamento_itens', 'quote_id', 'orcamento_id'),
    ('orcamento_itens', 'product_id', 'produto_id'),
    ('eventos', 'quote_id', 'orcamento_id'),
    ('eventos', 'order_id', 'pedido_id'),
    ('movimentos', 'trf_id', 'transferencia_id'),
    ('produtos', 'category_id', 'categoria_id'),
    ('produto_insumos', 'product_id', 'produto_id'),
    ('produto_insumos', 'ingredient_id', 'insumo_id'),
    ('insumo_conversoes', 'ingredient_id', 'insumo_id'),
    ('compras', 'movto_id', 'movimento_id'),
    ('producao_produtos', 'order_id', 'pedido_id'),
    ('producao_produtos', 'product_id', 'produto_id'),
]

# (nome, tabela, colunas_locais, tabela_ref, colunas_ref)
_CREATES = [
    ('compra_itens_insumo_id_fkey', 'compra_itens', ['insumo_id'], 'insumos', ['id']),
    ('compras_movimento_id_fkey', 'compras', ['movimento_id'], 'movimentos', ['id']),
    ('eventos_pedido_id_fkey', 'eventos', ['pedido_id'], 'pedidos', ['id']),
    ('eventos_orcamento_id_fkey', 'eventos', ['orcamento_id'], 'orcamentos', ['id']),
    ('movimentos_conta_id_fkey', 'movimentos', ['conta_id'], 'conta', ['id']),
    ('movimentos_recurso_id_fkey', 'movimentos', ['recurso_id'], 'recurso', ['id']),
    ('movimentos_previsao_id_fkey', 'movimentos', ['previsao_id'], 'previsao', ['id']),
    ('movimentos_operacao_id_fkey', 'movimentos', ['operacao_id'], 'operacao', ['id']),
    ('movimentos_transferencia_id_fkey', 'movimentos', ['transferencia_id'], 'transferencias', ['id']),
    ('pedido_itens_pedido_id_fkey', 'pedido_itens', ['pedido_id'], 'pedidos', ['id']),
    ('pedido_itens_produto_id_fkey', 'pedido_itens', ['produto_id'], 'produtos', ['id']),
    ('fk_pedidos_producao', 'pedidos', ['producao_id'], 'producao', ['id']),
    ('fk_pedidos_orcamentos', 'pedidos', ['orcamento_id'], 'orcamentos', ['id']),
    ('pedidos_carteira_id_fkey', 'pedidos', ['carteira_id'], 'carteira', ['id']),
    ('pedidos_conta_id_fkey', 'pedidos', ['conta_id'], 'conta', ['id']),
    ('pedidos_movimento_id_fkey', 'pedidos', ['movimento_id'], 'movimentos', ['id']),
    ('pedidos_transacao_id_fkey', 'pedidos', ['transacao_id'], 'transacao', ['id']),
    ('producao_insumos_insumo_id_fkey', 'producao_insumos', ['insumo_id'], 'insumos', ['id']),
    ('producao_produtos_pedido_id_fkey', 'producao_produtos', ['pedido_id'], 'pedidos', ['id']),
    ('producao_produtos_produto_id_fkey', 'producao_produtos', ['produto_id'], 'produtos', ['id']),
    ('produto_insumos_produto_id_fkey', 'produto_insumos', ['produto_id'], 'produtos', ['id']),
    ('produto_insumos_insumo_id_fkey', 'produto_insumos', ['insumo_id'], 'insumos', ['id']),
    ('fk_produtos_categorias', 'produtos', ['categoria_id'], 'categorias', ['id']),
    ('orcamento_itens_produto_id_fkey', 'orcamento_itens', ['produto_id'], 'produtos', ['id']),
    ('orcamento_itens_orcamento_id_fkey', 'orcamento_itens', ['orcamento_id'], 'orcamentos', ['id']),
    ('fk_orcamentos_pedidos', 'orcamentos', ['pedido_id'], 'pedidos', ['id']),
    ('orcamentos_carteira_id_fkey', 'orcamentos', ['carteira_id'], 'carteira', ['id']),
    ('insumo_conversoes_insumo_id_fkey', 'insumo_conversoes', ['insumo_id'], 'insumos', ['id']),
]

# (constraint, tabela) recriadas no downgrade (nomes originais).
_RECREATES = [
    ('compra_itens_insumo_id_fkey', 'compra_itens', ['insumo_id'], 'ingredients', ['id']),
    ('compras_movto_id_fkey', 'compras', ['movto_id'], 'movto', ['id']),
    ('events_order_id_fkey', 'events', ['order_id'], 'orders', ['id']),
    ('events_quote_id_fkey', 'events', ['quote_id'], 'quotes', ['id']),
    ('movto_conta_id_fkey', 'movto', ['conta_id'], 'conta', ['id']),
    ('movto_recurso_id_fkey', 'movto', ['recurso_id'], 'recurso', ['id']),
    ('movto_previsao_id_fkey', 'movto', ['previsao_id'], 'previsao', ['id']),
    ('movto_operacao_id_fkey', 'movto', ['operacao_id'], 'operacao', ['id']),
    ('movto_trf_id_fkey', 'movto', ['trf_id'], 'recurso_trf', ['id']),
    ('order_items_order_id_fkey', 'order_items', ['order_id'], 'orders', ['id']),
    ('order_items_product_id_fkey', 'order_items', ['product_id'], 'products', ['id']),
    ('fk_orders_producao', 'orders', ['producao_id'], 'producao', ['id']),
    ('fk_orders_quotes', 'orders', ['quote_id'], 'quotes', ['id']),
    ('orders_carteira_id_fkey', 'orders', ['carteira_id'], 'carteira', ['id']),
    ('orders_client_id_fkey', 'orders', ['client_id'], 'conta', ['id']),
    ('orders_movto_id_fkey', 'orders', ['movto_id'], 'movto', ['id']),
    ('orders_transacao_id_fkey', 'orders', ['transacao_id'], 'transacao', ['id']),
    ('producao_insumos_insumo_id_fkey', 'producao_insumos', ['insumo_id'], 'ingredients', ['id']),
    ('producao_produtos_order_id_fkey', 'producao_produtos', ['order_id'], 'orders', ['id']),
    ('producao_produtos_product_id_fkey', 'producao_produtos', ['product_id'], 'products', ['id']),
    ('product_ingredients_ingredient_id_fkey', 'product_ingredients', ['ingredient_id'], 'ingredients', ['id']),
    ('product_ingredients_product_id_fkey', 'product_ingredients', ['product_id'], 'products', ['id']),
    ('fk_products_category_id', 'products', ['category_id'], 'categories', ['id']),
    ('quote_items_product_id_fkey', 'quote_items', ['product_id'], 'products', ['id']),
    ('quote_items_quote_id_fkey', 'quote_items', ['quote_id'], 'quotes', ['id']),
    ('fk_quotes_orders', 'quotes', ['pedido_id'], 'orders', ['id']),
    ('quotes_carteira_id_fkey', 'quotes', ['carteira_id'], 'carteira', ['id']),
    ('unit_conversions_ingredient_id_fkey', 'unit_conversions', ['ingredient_id'], 'ingredients', ['id']),
]

# (sequence_antiga, sequence_nova)
_SEQUENCES = [
    ('categories_id_seq', 'categorias_id_seq'),
    ('events_id_seq', 'eventos_id_seq'),
    ('ingredients_id_seq', 'insumos_id_seq'),
    ('movto_id_seq', 'movimentos_id_seq'),
    ('order_items_id_seq', 'pedido_itens_id_seq'),
    ('orders_id_seq', 'pedidos_id_seq'),
    ('products_id_seq', 'produtos_id_seq'),
    ('quote_items_id_seq', 'orcamento_itens_id_seq'),
    ('quotes_id_seq', 'orcamentos_id_seq'),
    ('settings_id_seq', 'configuracoes_id_seq'),
    ('unit_conversions_id_seq', 'insumo_conversoes_id_seq'),
    ('users_id_seq', 'usuarios_id_seq'),
    ('trf_id_seq', 'transferencias_id_seq'),
]


def _drop_fk(name, table):
    op.execute(f'ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}')


def upgrade():
    for name, table in _DROPS:
        _drop_fk(name, table)
    for old, new in _TABLES:
        op.rename_table(old, new)
    for table, old, new in _COLUMNS:
        op.alter_column(table, old, new_column_name=new)
    for name, table, _local, _ref, _refcol in _CREATES:
        _drop_fk(name, table)  # protege re-execucao (tabelas novas ja existem aqui)
    for name, table, local, ref, refcol in _CREATES:
        op.create_foreign_key(name, table, ref, local, refcol)
    for old, new in _SEQUENCES:
        op.execute(f'ALTER SEQUENCE IF EXISTS {old} RENAME TO {new}')


def downgrade():
    for name, table, _local, _ref, _refcol in _CREATES:
        _drop_fk(name, table)
    for table, old, new in _COLUMNS:
        op.alter_column(table, new, new_column_name=old)
    for old, new in _TABLES:
        op.rename_table(new, old)
    for name, table, _local, _ref, _refcol in _RECREATES:
        _drop_fk(name, table)  # protege re-execucao (tabelas antigas ja existem aqui)
    for name, table, local, ref, refcol in _RECREATES:
        op.create_foreign_key(name, table, ref, local, refcol)
    for old, new in _SEQUENCES:
        op.execute(f'ALTER SEQUENCE IF EXISTS {new} RENAME TO {old}')
