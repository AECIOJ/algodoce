"""remove tempo_producao from products

Revision ID: af3c2b9e4d81
Revises: 97608961c665
Create Date: 2026-05-18 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'af3c2b9e4d81'
down_revision = '97608961c665'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS tempo_producao")


def downgrade():
    op.add_column('products', sa.Column('tempo_producao', sa.Integer(), nullable=True))
