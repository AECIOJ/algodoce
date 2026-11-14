"""pedido renames: previsao_entrega/data_fatura/data_cancelado/data_entrega

Revision ID: e2f3a4b5c6d7
Revises: d1f2a3b4c5e6
Create Date: 2026-11-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e2f3a4b5c6d7'
down_revision = 'd1f2a3b4c5e6'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('pedidos', 'data_previsao_entrega',
                    new_column_name='previsao_entrega',
                    existing_type=sa.DateTime())
    op.alter_column('pedidos', 'entregue_em', new_column_name='data_entrega',
                    existing_type=sa.Date())
    op.alter_column('pedidos', 'faturado_em', new_column_name='data_fatura',
                    existing_type=sa.Date())
    op.alter_column('pedidos', 'cancelado_em', new_column_name='data_cancelado',
                    existing_type=sa.Date())


def downgrade():
    op.alter_column('pedidos', 'data_cancelado',
                    new_column_name='cancelado_em', existing_type=sa.Date())
    op.alter_column('pedidos', 'data_fatura', new_column_name='faturado_em',
                    existing_type=sa.Date())
    op.alter_column('pedidos', 'data_entrega',
                    new_column_name='entregue_em', existing_type=sa.Date())
    op.alter_column('pedidos', 'previsao_entrega',
                    new_column_name='data_previsao_entrega',
                    existing_type=sa.DateTime())
