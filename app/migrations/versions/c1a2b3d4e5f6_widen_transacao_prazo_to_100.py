"""transacao.prazo: alargar para String(100)

Revision ID: c1a2b3d4e5f6
Revises: b0a1c2d3e4f5
Create Date: 2026-09-21

O `prazo` passa a receber, verbatim, o `prazo_recebimento` da carteira
(String(100)); alinha a largura da coluna em `transacao` à da origem.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1a2b3d4e5f6'
down_revision = 'b0a1c2d3e4f5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('transacao', schema=None) as batch_op:
        batch_op.alter_column('prazo', existing_type=sa.String(50),
                              type_=sa.String(100), existing_nullable=False,
                              existing_server_default='')


def downgrade():
    with op.batch_alter_table('transacao', schema=None) as batch_op:
        batch_op.alter_column('prazo', existing_type=sa.String(100),
                              type_=sa.String(50), existing_nullable=False,
                              existing_server_default='')
