"""change rubrica tipo from string to integer (1=Receitas, 2=Despesas)

Revision ID: ccc2d3e4f5a6
Revises: bbb1c2d3e4f5
Create Date: 2026-06-22 10:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "ccc2d3e4f5a6"
down_revision = "bbb1c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("rubrica", sa.Column("tipo_int", sa.Integer(), server_default=sa.text("1")))
    op.execute("UPDATE rubrica SET tipo_int = CASE WHEN tipo = 'P' THEN 1 WHEN tipo = 'R' THEN 2 ELSE 1 END")
    op.drop_column("rubrica", "tipo")
    op.alter_column("rubrica", "tipo_int", new_column_name="tipo")


def downgrade():
    op.add_column("rubrica", sa.Column("tipo_old", sa.String(1), server_default=sa.text("'R'")))
    op.execute("UPDATE rubrica SET tipo_old = CASE WHEN tipo = 1 THEN 'P' WHEN tipo = 2 THEN 'R' ELSE 'R' END")
    op.drop_column("rubrica", "tipo")
    op.alter_column("rubrica", "tipo_old", new_column_name="tipo")
