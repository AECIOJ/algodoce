"""remove data_criacao from producao

Revision ID: f8e9d0c1b2a4
Revises: a8b9c0d1e2f3
Create Date: 2026-06-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
revision = 'f8e9d0c1b2a4'
down_revision = 'a8b9c0d1e2f3'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('producao', 'data_criacao')


def downgrade():
    op.add_column('producao', sa.Column(
        'data_criacao', sa.DateTime(), nullable=False,
        server_default=sa.func.now()
    ))
