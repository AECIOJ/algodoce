"""add trf table and trf_id to movto

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-07-13 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3c4d5e6f7a8'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('trf',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('data', sa.Date(), nullable=False),
        sa.Column('historico', sa.Text(), nullable=True),
        sa.Column('total', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id')
    )

    op.add_column('movto', sa.Column('trf_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'movto', 'trf', ['trf_id'], ['id'])


def downgrade():
    with op.batch_alter_table('movto', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('trf_id')

    op.drop_table('trf')
