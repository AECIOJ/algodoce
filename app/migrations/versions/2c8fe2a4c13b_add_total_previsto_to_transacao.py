"""add total_previsto to transacao

Revision ID: 2c8fe2a4c13b
Revises: 5096816c1660
Create Date: 2026-06-30 11:27:34.045594

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2c8fe2a4c13b'
down_revision = '5096816c1660'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('transacao', schema=None) as batch_op:
        batch_op.add_column(sa.Column('total_previsto', sa.Numeric(precision=12, scale=2),
                                      nullable=False, server_default=sa.text('0')))
    op.execute("UPDATE transacao SET total_previsto = COALESCE((SELECT SUM(previsto) FROM previsao WHERE previsao.transacao_id = transacao.id), 0)")


def downgrade():
    with op.batch_alter_table('transacao', schema=None) as batch_op:
        batch_op.drop_column('total_previsto')
