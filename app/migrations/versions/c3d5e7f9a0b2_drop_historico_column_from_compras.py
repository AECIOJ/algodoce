"""drop historico column from compras

Revision ID: c3d5e7f9a0b2
Revises: b2c4d6e8f0a1
Create Date: 2026-09-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d5e7f9a0b2'
down_revision = 'b2c4d6e8f0a1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('compras', schema=None) as batch_op:
        batch_op.drop_column('historico')


def downgrade():
    with op.batch_alter_table('compras', schema=None) as batch_op:
        batch_op.add_column(sa.Column('historico', sa.Text(), nullable=True))