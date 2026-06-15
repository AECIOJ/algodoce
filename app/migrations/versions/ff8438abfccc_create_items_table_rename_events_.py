"""create items table, rename events.complemento to obs, migrate order/quote status to int

Revision ID: ff8438abfccc
Revises: d536bf4d6886
Create Date: 2026-06-13 08:32:03.019294

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'ff8438abfccc'
down_revision = 'd536bf4d6886'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create items table
    op.create_table('items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quote_id', sa.Integer(), nullable=True),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantidade', sa.Integer(), nullable=False),
        sa.Column('preco_unitario', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('observacao', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. Migrate data from quote_items → items (set quote_id only)
    op.execute("""
        INSERT INTO items (quote_id, order_id, product_id, quantidade, preco_unitario, observacao)
        SELECT quote_id, NULL, product_id, quantidade, preco_unitario, observacao
        FROM quote_items
    """)
    # 3. Migrate data from order_items → items (set order_id only)
    op.execute("""
        INSERT INTO items (quote_id, order_id, product_id, quantidade, preco_unitario, observacao)
        SELECT NULL, order_id, product_id, quantidade, preco_unitario, observacao
        FROM order_items
    """)

    # 4. Drop old tables
    op.drop_table('order_items')
    op.drop_table('quote_items')

    # 5. Rename events.complemento → obs (add column, copy data, drop old)
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('obs', sa.Text(), nullable=True))
    op.execute("UPDATE events SET obs = complemento WHERE complemento IS NOT NULL")
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.drop_column('complemento')

    # 6. Convert orders.status from varchar to int
    #    Map: 'rascunho'/'pendente' → 0, 'em_producao' → 1, 'pronto' → 2, 'entregue' → 9, 'cancelado' → 3
    #    Drop the varchar default first, then change type, then set integer default
    op.execute("ALTER TABLE orders ALTER COLUMN status DROP DEFAULT")
    op.execute("""
        UPDATE orders SET status = CASE
            WHEN status IN ('rascunho', 'pendente') THEN '0'
            WHEN status = 'em_producao' THEN '1'
            WHEN status = 'pronto' THEN '2'
            WHEN status = 'entregue' THEN '9'
            WHEN status = 'cancelado' THEN '3'
            ELSE '0'
        END
    """)
    op.execute("ALTER TABLE orders ALTER COLUMN status TYPE INTEGER USING status::integer")
    op.execute("ALTER TABLE orders ALTER COLUMN status SET DEFAULT '0'")

    # 7. quotes.status is already Integer; no migration needed


def downgrade():
    # Reverse: convert int back to varchar
    op.execute("ALTER TABLE orders ALTER COLUMN status DROP DEFAULT")
    op.execute("""
        UPDATE orders SET status = CASE
            WHEN status = 0 THEN 'pendente'
            WHEN status = 1 THEN 'em_producao'
            WHEN status = 2 THEN 'pronto'
            WHEN status = 9 THEN 'entregue'
            WHEN status = 3 THEN 'cancelado'
            ELSE 'pendente'
        END
    """)
    op.execute("ALTER TABLE orders ALTER COLUMN status TYPE VARCHAR(20) USING status::varchar")
    op.execute("ALTER TABLE orders ALTER COLUMN status SET DEFAULT 'rascunho'")

    # Restore events.complemento from obs
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('complemento', sa.TEXT(), autoincrement=False, nullable=True))
    op.execute("UPDATE events SET complemento = obs")
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.drop_column('obs')

    # Recreate old tables
    op.create_table('quote_items',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('quote_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('product_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('quantidade', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('preco_unitario', sa.NUMERIC(precision=10, scale=2), autoincrement=False, nullable=True),
        sa.Column('observacao', sa.TEXT(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('quote_items_product_id_fkey')),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], name=op.f('quote_items_quote_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('quote_items_pkey'))
    )
    op.create_table('order_items',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('order_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('product_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('quantidade', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('preco_unitario', sa.NUMERIC(precision=10, scale=2), autoincrement=False, nullable=True),
        sa.Column('observacao', sa.TEXT(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name=op.f('order_items_order_id_fkey')),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('order_items_product_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('order_items_pkey'))
    )

    # Move data back from items to old tables
    op.execute("""
        INSERT INTO quote_items (quote_id, product_id, quantidade, preco_unitario, observacao)
        SELECT quote_id, product_id, quantidade, preco_unitario, observacao
        FROM items WHERE quote_id IS NOT NULL
    """)
    op.execute("""
        INSERT INTO order_items (order_id, product_id, quantidade, preco_unitario, observacao)
        SELECT order_id, product_id, quantidade, preco_unitario, observacao
        FROM items WHERE order_id IS NOT NULL
    """)

    op.drop_table('items')
