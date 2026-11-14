"""orcamento data: rename data_pedido para data

Revision ID: a8c9d0e1f2b3
Revises: c4d5e6f7a8b9
Create Date: 2026-11-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a8c9d0e1f2b3'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('orcamentos', 'data_pedido', new_column_name='data',
                    existing_type=sa.DateTime())


def downgrade():
    op.alter_column('orcamentos', 'data', new_column_name='data_pedido',
                    existing_type=sa.DateTime())
