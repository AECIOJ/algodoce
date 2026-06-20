"""add producao_produtos table

Revision ID: f7e6d5c4b3a3
Revises: f7e6d5c4b3a2
Create Date: 2026-06-18 10:02:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'f7e6d5c4b3a3'
down_revision = 'f7e6d5c4b3a2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('producao_produtos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('producao_id', sa.Integer(), sa.ForeignKey('producao.id'), nullable=False),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id'), nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('quantidade', sa.Integer(), nullable=False),
        sa.Column('produzido', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('etapa_atual_id', sa.Integer(), sa.ForeignKey('etapas.id'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('producao_produtos')
