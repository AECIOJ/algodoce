"""rename compras.compra_em to faturado_em

Revision ID: e5f7a9b1c3d6
Revises: d4e6f8a0b2c4
Create Date: 2026-09-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e5f7a9b1c3d6'
down_revision = 'd4e6f8a0b2c4'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('compras', 'compra_em', new_column_name='faturado_em',
                    existing_type=sa.Date())


def downgrade():
    op.alter_column('compras', 'faturado_em', new_column_name='compra_em',
                    existing_type=sa.Date())