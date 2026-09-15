"""drop sincronizar from movimentos

Revision ID: a4b5c6d7e8f9
Revises: f1a2b3c4d5e6
Create Date: 2026-09-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a4b5c6d7e8f9'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('movimentos', 'sincronizar')


def downgrade():
    op.add_column(
        'movimentos',
        sa.Column('sincronizar', sa.Boolean(), nullable=False,
                  server_default=sa.true()),
    )