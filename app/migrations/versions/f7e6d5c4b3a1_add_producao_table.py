"""add producao table

Revision ID: f7e6d5c4b3a1
Revises: b77099a0bb68
Create Date: 2026-06-18 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'f7e6d5c4b3a1'
down_revision = 'f6e5d4c3b2a2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('producao',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('descricao', sa.String(200), nullable=False),
        sa.Column('data_criacao', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('data_fim', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='andamento'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('producao')
