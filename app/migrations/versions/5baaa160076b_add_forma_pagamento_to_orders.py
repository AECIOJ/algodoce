"""add forma_pagamento to orders

Revision ID: 5baaa160076b
Revises: 1f183ca1067f
Create Date: 2026-06-20 10:02:30.421741

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5baaa160076b'
down_revision = '1f183ca1067f'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('forma_pagamento', sa.Integer(),
                                      server_default='0', nullable=False))


def downgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('forma_pagamento')
