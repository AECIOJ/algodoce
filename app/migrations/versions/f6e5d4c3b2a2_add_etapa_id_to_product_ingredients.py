"""add etapa_id to product_ingredients

Revision ID: f6e5d4c3b2a2
Revises: b77099a0bb68
Create Date: 2026-06-18 08:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'f6e5d4c3b2a2'
down_revision = 'b77099a0bb68'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('ALTER TABLE product_ingredients DROP CONSTRAINT IF EXISTS fk_pi_etapa_id')
    op.execute('ALTER TABLE product_ingredients DROP CONSTRAINT IF EXISTS product_ingredients_etapa_id_fkey')
    with op.batch_alter_table('product_ingredients', schema=None) as batch_op:
        batch_op.add_column(sa.Column('etapa_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_pi_etapa_id', 'etapas', ['etapa_id'], ['id'])


def downgrade():
    op.execute('ALTER TABLE product_ingredients DROP CONSTRAINT IF EXISTS fk_pi_etapa_id')
    op.execute('ALTER TABLE product_ingredients DROP CONSTRAINT IF EXISTS product_ingredients_etapa_id_fkey')
    with op.batch_alter_table('product_ingredients', schema=None) as batch_op:
        batch_op.drop_column('etapa_id')
