"""create rubrica table

Revision ID: bbb1c2d3e4f5
Revises: ad2413d5b9a5
Create Date: 2026-06-22 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "bbb1c2d3e4f5"
down_revision = "ad2413d5b9a5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rubrica",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("tipo", sa.String(1), nullable=False, server_default=sa.text("'R'")),
        sa.Column("pai_id", sa.Integer(), nullable=True),
        sa.Column("ativa", sa.Boolean(), default=True),
    )
    op.create_foreign_key(
        "fk_rubrica_pai_id",
        "rubrica", "rubrica",
        ["pai_id"], ["id"],
    )


def downgrade():
    op.drop_constraint("fk_rubrica_pai_id", "rubrica", type_="foreignkey")
    op.drop_table("rubrica")
