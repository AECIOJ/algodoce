"""remove legacy forma_pagamento, add taxa_prazo fields

Revision ID: 132fb07696d9
Revises: d5ff48124a39
Create Date: 2026-06-27 12:05:33.357825

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '132fb07696d9'
down_revision = 'd5ff48124a39'
branch_labels = None
depends_on = None


def upgrade():
    # --- forma_pagamento ---
    with op.batch_alter_table('forma_pagamento', schema=None) as batch_op:
        batch_op.add_column(sa.Column('taxa_padrao', sa.Numeric(precision=5, scale=2), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('prazo_recebimento', sa.String(length=100), nullable=True))
    op.execute("ALTER TABLE forma_pagamento ALTER COLUMN taxa_padrao DROP DEFAULT")

    # --- orders: backfill then NOT NULL + drop legacy ---
    op.execute("UPDATE orders SET forma_pagamento_id = 1 WHERE forma_pagamento_id IS NULL")
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.alter_column('forma_pagamento_id',
               existing_type=sa.INTEGER(),
               nullable=False)
        batch_op.drop_column('forma_pagamento')

    # --- previsao ---
    with op.batch_alter_table('previsao', schema=None) as batch_op:
        batch_op.add_column(sa.Column('forma_pagamento_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('taxa', sa.Numeric(precision=5, scale=2), nullable=False, server_default=sa.text('0')))
        batch_op.create_foreign_key(None, 'forma_pagamento', ['forma_pagamento_id'], ['id'])
    op.execute("ALTER TABLE previsao ALTER COLUMN taxa DROP DEFAULT")

    # --- quotes: backfill then NOT NULL + drop legacy ---
    op.execute("UPDATE quotes SET forma_pagamento_id = 1 WHERE forma_pagamento_id IS NULL")
    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.alter_column('forma_pagamento_id',
               existing_type=sa.INTEGER(),
               nullable=False)
        batch_op.drop_column('forma_pagamento')


def downgrade():
    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('forma_pagamento', sa.INTEGER(), autoincrement=False, nullable=False, server_default=sa.text('0')))
        batch_op.alter_column('forma_pagamento_id',
               existing_type=sa.INTEGER(),
               nullable=True)

    with op.batch_alter_table('previsao', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('taxa')
        batch_op.drop_column('forma_pagamento_id')

    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('forma_pagamento', sa.INTEGER(), autoincrement=False, nullable=False, server_default=sa.text('0')))
        batch_op.alter_column('forma_pagamento_id',
               existing_type=sa.INTEGER(),
               nullable=True)

    with op.batch_alter_table('forma_pagamento', schema=None) as batch_op:
        batch_op.drop_column('prazo_recebimento')
        batch_op.drop_column('taxa_padrao')
