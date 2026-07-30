"""rename etapa_id to etapa

Revision ID: a33cc96da528
Revises: c7d8e9f0a1b2
Create Date: 2026-07-29 11:03:44.627872

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a33cc96da528'
down_revision = 'c7d8e9f0a1b2'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('product_ingredients', 'etapa_id', new_column_name='etapa')


def downgrade():
    op.alter_column('product_ingredients', 'etapa', new_column_name='etapa_id')
