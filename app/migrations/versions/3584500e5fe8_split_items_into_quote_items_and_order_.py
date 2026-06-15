"""split items into quote_items and order_items

Revision ID: 3584500e5fe8
Revises: ff8438abfccc
Create Date: 2026-06-14 07:08:21.486338

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3584500e5fe8'
down_revision = 'ff8438abfccc'
branch_labels = None
depends_on = None


def upgrade():
    # Create new tables
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

    # Migrate data from items to quote_items (where quote_id IS NOT NULL)
    op.execute("""
        INSERT INTO quote_items (quote_id, product_id, quantidade, preco_unitario, observacao)
        SELECT quote_id, product_id, quantidade, preco_unitario, observacao
        FROM items
        WHERE quote_id IS NOT NULL
    """)

    # Migrate data from items to order_items (where order_id IS NOT NULL)
    op.execute("""
        INSERT INTO order_items (order_id, product_id, quantidade, preco_unitario, observacao)
        SELECT order_id, product_id, quantidade, preco_unitario, observacao
        FROM items
        WHERE order_id IS NOT NULL
    """)

    # Drop old unified table
    op.drop_table('items')


def downgrade():
    # Recreate old unified table
    op.create_table('items',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('quote_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('order_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('product_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('quantidade', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('preco_unitario', sa.NUMERIC(precision=10, scale=2), autoincrement=False, nullable=True),
        sa.Column('observacao', sa.TEXT(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name=op.f('items_order_id_fkey')),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('items_product_id_fkey')),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], name=op.f('items_quote_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('items_pkey'))
    )

    # Restore data from quote_items
    op.execute("""
        INSERT INTO items (quote_id, product_id, quantidade, preco_unitario, observacao)
        SELECT quote_id, product_id, quantidade, preco_unitario, observacao
        FROM quote_items
    """)

    # Restore data from order_items
    op.execute("""
        INSERT INTO items (order_id, product_id, quantidade, preco_unitario, observacao)
        SELECT order_id, product_id, quantidade, preco_unitario, observacao
        FROM order_items
    """)

    op.drop_table('quote_items')
    op.drop_table('order_items')
