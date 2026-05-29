"""add unidade to product_ingredients and create unit_conversions

Revision ID: d3c1b5f7e902
Revises: af3c2b9e4d81
Create Date: 2026-05-18 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd3c1b5f7e902'
down_revision = 'af3c2b9e4d81'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'product_ingredients',
        sa.Column('unidade', sa.String(20), nullable=False, server_default='un'),
    )
    op.execute("""
        CREATE TABLE IF NOT EXISTS unit_conversions (
            id SERIAL PRIMARY KEY,
            ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
            unidade VARCHAR(20) NOT NULL,
            fator NUMERIC(10, 6) NOT NULL
        )
    """)


def downgrade():
    op.drop_column('product_ingredients', 'unidade')
    op.execute("DROP TABLE IF EXISTS unit_conversions")
