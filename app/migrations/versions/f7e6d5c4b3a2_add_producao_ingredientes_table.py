"""add producao_ingredientes table

Revision ID: f7e6d5c4b3a2
Revises: f7e6d5c4b3a1
Create Date: 2026-06-18 10:01:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'f7e6d5c4b3a2'
down_revision = 'f7e6d5c4b3a1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('producao_ingredientes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('producao_id', sa.Integer(), sa.ForeignKey('producao.id'), nullable=False),
        sa.Column('ingrediente_id', sa.Integer(), sa.ForeignKey('ingredients.id'), nullable=False),
        sa.Column('quantidade', sa.Numeric(10, 3), nullable=False),
        sa.Column('comprado', sa.Numeric(10, 3), nullable=False, server_default=sa.text('0')),
        sa.Column('unidade', sa.String(20), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('producao_ingredientes')
