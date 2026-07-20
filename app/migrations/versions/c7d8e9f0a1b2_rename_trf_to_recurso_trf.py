"""rename trf to recurso_trf

Revision ID: c7d8e9f0a1b2
Revises: f6a5b4c3d2e1
Create Date: 2026-07-20 12:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'c7d8e9f0a1b2'
down_revision = 'f6a5b4c3d2e1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('movto', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')

    op.rename_table('trf', 'recurso_trf')

    with op.batch_alter_table('movto', schema=None) as batch_op:
        batch_op.create_foreign_key(None, 'recurso_trf', ['trf_id'], ['id'])


def downgrade():
    with op.batch_alter_table('movto', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')

    op.rename_table('recurso_trf', 'trf')

    with op.batch_alter_table('movto', schema=None) as batch_op:
        batch_op.create_foreign_key(None, 'trf', ['trf_id'], ['id'])
