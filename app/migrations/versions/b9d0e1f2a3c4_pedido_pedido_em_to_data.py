"""pedido data: rename pedido_em para data

Revision ID: b9d0e1f2a3c4
Revises: a8c9d0e1f2b3
Create Date: 2026-11-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b9d0e1f2a3c4'
down_revision = 'a8c9d0e1f2b3'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('pedidos', 'pedido_em', new_column_name='data',
                    existing_type=sa.Date())


def downgrade():
    op.alter_column('pedidos', 'data', new_column_name='pedido_em',
                    existing_type=sa.Date())
