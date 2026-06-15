"""add users table for admin auth

Revision ID: def789abc012
Revises: abc123def456
Create Date: 2026-06-10 12:05:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "def789abc012"
down_revision = "abc123def456"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(80), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(256), nullable=False),
    )


def downgrade():
    op.drop_table("users")
