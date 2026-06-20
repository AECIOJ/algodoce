"""add forma_pagamento to quotes

Revision ID: 3c35784ad38b
Revises: 10ba39a080e3
Create Date: 2026-06-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '3c35784ad38b'
down_revision = '10ba39a080e3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('forma_pagamento', sa.Integer(), nullable=False, server_default=sa.text('0')))


def downgrade():
    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.drop_column('forma_pagamento')
