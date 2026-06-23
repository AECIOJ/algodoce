"""drop status from previsoes

Revision ID: 8597fd57639d
Revises: f3a4c73bd1d9
Create Date: 2026-06-22 09:48:43.936913

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8597fd57639d'
down_revision = 'f3a4c73bd1d9'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('previsoes', 'status')


def downgrade():
    op.add_column('previsoes', sa.Column('status', sa.Integer(), nullable=False,
                                         server_default='0'))
