"""pedido data date to datetime

Revision ID: c0e1f2a3b4d5
Revises: b9d0e1f2a3c4
Create Date: 2026-11-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c0e1f2a3b4d5'
down_revision = 'b9d0e1f2a3c4'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('pedidos', 'data',
                    existing_type=sa.Date(), type_=sa.DateTime())


def downgrade():
    op.alter_column('pedidos', 'data',
                    existing_type=sa.DateTime(), type_=sa.Date())
