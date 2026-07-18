"""rename compra_eventos to compra_historico

Revision ID: f6a5b4c3d2e1
Revises: efe49ca52245
Create Date: 2026-07-17 10:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'f6a5b4c3d2e1'
down_revision = '43f2fee87f18'
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table('compra_eventos', 'compra_historico')
    op.alter_column('compra_historico', 'evento', new_column_name='status')


def downgrade():
    op.alter_column('compra_historico', 'status', new_column_name='evento')
    op.rename_table('compra_historico', 'compra_eventos')
