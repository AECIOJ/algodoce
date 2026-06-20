"""add forminhas to quotes and orders

Revision ID: ad2413d5b9a5
Revises: 5baaa160076b
Create Date: 2026-06-20 10:10:33.179982

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ad2413d5b9a5'
down_revision = '5baaa160076b'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('forminhas', sa.Integer(),
                                      server_default='0', nullable=False))

    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('forminhas', sa.Integer(),
                                      server_default='0', nullable=False))


def downgrade():
    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.drop_column('forminhas')

    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('forminhas')
