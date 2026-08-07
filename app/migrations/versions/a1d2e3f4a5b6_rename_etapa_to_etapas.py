"""rename etapa to etapas (multi-codes)

Revision ID: a1d2e3f4a5b6
Revises: a33cc96da528
Create Date: 2026-08-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1d2e3f4a5b6'
down_revision = 'a33cc96da528'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'product_ingredients', 'etapa',
        new_column_name='etapas',
        existing_type=sa.Integer(),
        type_=sa.String(10),
    )


def downgrade():
    op.alter_column(
        'product_ingredients', 'etapas',
        new_column_name='etapa',
        existing_type=sa.String(10),
        type_=sa.Integer(),
    )
