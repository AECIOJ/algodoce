"""backfill order.quote_id from quote.pedido_id

Revision ID: b4c3a1d9e8f7
Revises: 3584500e5fe8
Create Date: 2026-06-14 09:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'b4c3a1d9e8f7'
down_revision = '3584500e5fe8'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        UPDATE orders
        SET quote_id = quotes.id
        FROM quotes
        WHERE quotes.pedido_id = orders.id
        AND orders.quote_id IS NULL
    """)


def downgrade():
    pass
