"""add ordem column to rubrica

Revision ID: eee4f5a6b7c8
Revises: ddd3e4f5a6b7
Create Date: 2026-06-22 11:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "eee4f5a6b7c8"
down_revision = "ddd3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("rubrica", sa.Column("ordem", sa.Integer(), nullable=False, server_default=sa.text("0")))


def downgrade():
    op.drop_column("rubrica", "ordem")
