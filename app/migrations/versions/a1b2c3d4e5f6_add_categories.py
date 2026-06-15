"""add categories table and category_id to products

Revision ID: a1b2c3d4e5f6
Revises: def789abc012
Create Date: 2026-06-10 12:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "def789abc012"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("ativo", sa.Boolean(), default=True),
        sa.Column("ordem", sa.Integer(), default=0),
    )
    op.add_column("products", sa.Column("category_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_products_category_id",
        "products",
        "categories",
        ["category_id"],
        ["id"],
    )


def downgrade():
    op.drop_constraint("fk_products_category_id", "products", type_="foreignkey")
    op.drop_column("products", "category_id")
    op.drop_table("categories")
