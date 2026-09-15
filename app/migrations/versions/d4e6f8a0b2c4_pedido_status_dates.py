"""pedido status dates: rename data para _em, add faturado_em/cancelado_em

Revision ID: d4e6f8a0b2c4
Revises: c3d5e7f9a0b2
Create Date: 2026-09-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4e6f8a0b2c4'
down_revision = 'c3d5e7f9a0b2'
branch_labels = None
depends_on = None


def upgrade():
    # Renomear datas com o padrão <status>_em (Date, alinhado à compra)
    op.alter_column('pedidos', 'data_pedido', new_column_name='pedido_em',
                    existing_type=sa.DateTime(), type_=sa.Date())
    op.alter_column('pedidos', 'data_entrega', new_column_name='entregue_em',
                    existing_type=sa.DateTime(), type_=sa.Date())
    # Novos campos de status
    op.add_column('pedidos', sa.Column('faturado_em', sa.Date(), nullable=True))
    op.add_column('pedidos', sa.Column('cancelado_em', sa.Date(), nullable=True))

    # Reordenar vocabulário PEDIDO_STATUS: legado 1(Produzindo)->2, 2(Pronto)->3
    # (produção é fase futura; sem datas, os valores são preservados raw).
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE pedidos SET status = 2 WHERE status = 1"))
    conn.execute(sa.text("UPDATE pedidos SET status = 3 WHERE status = 2"))


def downgrade():
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE pedidos SET status = 2 WHERE status = 3"))
    conn.execute(sa.text("UPDATE pedidos SET status = 1 WHERE status = 2"))
    op.drop_column('pedidos', 'cancelado_em')
    op.drop_column('pedidos', 'faturado_em')
    op.alter_column('pedidos', 'entregue_em', new_column_name='data_entrega',
                    existing_type=sa.Date(), type_=sa.DateTime())
    op.alter_column('pedidos', 'pedido_em', new_column_name='data_pedido',
                    existing_type=sa.Date(), type_=sa.DateTime())