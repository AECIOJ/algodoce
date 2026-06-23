"""add fator column to rubrica

Revision ID: ddd3e4f5a6b7
Revises: ccc2d3e4f5a6
Create Date: 2026-06-22 11:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "ddd3e4f5a6b7"
down_revision = "ccc2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("rubrica", sa.Column("fator", sa.Integer(), nullable=False, server_default=sa.text("1")))


def downgrade():
    op.drop_column("rubrica", "fator")
