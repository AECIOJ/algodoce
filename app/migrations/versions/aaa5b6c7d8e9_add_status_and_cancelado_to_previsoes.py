"""add status and cancelado to previsoes

Revision ID: aaa5b6c7d8e9
Revises: fff4a5b6c7d8
Create Date: 2026-06-22 13:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "aaa5b6c7d8e9"
down_revision = "fff4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("previsoes", sa.Column("status", sa.Integer(), nullable=False, server_default=sa.text("0")))
    op.add_column("previsoes", sa.Column("cancelado", sa.Date(), nullable=True))


def downgrade():
    op.drop_column("previsoes", "cancelado")
    op.drop_column("previsoes", "status")
