"""create previsoes table

Revision ID: fff4a5b6c7d8
Revises: eee4f5a6b7c8
Create Date: 2026-06-22 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "fff4a5b6c7d8"
down_revision = "eee4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "previsoes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("tipo", sa.String(1), nullable=False),
        sa.Column("conta_id", sa.Integer(), sa.ForeignKey("conta.id"), nullable=True),
        sa.Column("documento", sa.String(50), nullable=True),
        sa.Column("vencimento", sa.Date(), nullable=False),
        sa.Column("valor", sa.Numeric(12, 2), nullable=False),
        sa.Column("rubrica_id", sa.Integer(), sa.ForeignKey("rubrica.id"), nullable=True),
        sa.Column("historico", sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_table("previsoes")
