"""add variacao and sincronizar to movto

Revision ID: abcd1234ab01
Revises: 11898ad5f0af
Create Date: 2026-06-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'abcd1234ab01'
down_revision = '11898ad5f0af'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('movto', sa.Column('variacao', sa.Numeric(precision=12, scale=2), nullable=True, server_default=sa.text('0')))
    op.add_column('movto', sa.Column('sincronizar', sa.Boolean(), nullable=False, server_default=sa.text('true')))


def downgrade():
    op.drop_column('movto', 'sincronizar')
    op.drop_column('movto', 'variacao')
