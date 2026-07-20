"""rename trf to recurso_trf

Revision ID: c7d8e9f0a1b2
Revises: f6a5b4c3d2e1
Create Date: 2026-07-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c7d8e9f0a1b2'
down_revision = 'f6a5b4c3d2e1'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE movto
        DROP CONSTRAINT IF EXISTS movto_trf_id_fkey
    """)
    op.rename_table('trf', 'recurso_trf')
    op.create_foreign_key(
        'movto_trf_id_fkey', 'movto', 'recurso_trf', ['trf_id'], ['id']
    )


def downgrade():
    op.drop_constraint('movto_trf_id_fkey', 'movto', type_='foreignkey')
    op.rename_table('recurso_trf', 'trf')
    op.create_foreign_key(
        'movto_trf_id_fkey', 'movto', 'trf', ['trf_id'], ['id']
    )
