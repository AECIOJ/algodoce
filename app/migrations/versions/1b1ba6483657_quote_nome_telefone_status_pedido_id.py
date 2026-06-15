"""quote: nome/telefone, status, pedido_id

Revision ID: 1b1ba6483657
Revises: 44ba1d73b41e
Create Date: 2026-06-12 15:42:10.877857

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1b1ba6483657'
down_revision = '44ba1d73b41e'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add new columns as nullable first
    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cliente_nome', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('cliente_telefone', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('status', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('pedido_id', sa.Integer(), nullable=True))

    # 2. Migrate existing data from clients table
    op.execute("""
        UPDATE quotes
        SET cliente_nome = c.nome,
            cliente_telefone = c.telefone,
            status = 0
        FROM clients c
        WHERE quotes.client_id = c.id
    """)

    # 3. Make columns NOT NULL
    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.alter_column('cliente_nome', nullable=False)
        batch_op.alter_column('cliente_telefone', nullable=False)
        batch_op.alter_column('status', nullable=False)

    # 4. Drop old FK and columns, add new FK
    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.drop_constraint('quotes_client_id_fkey', type_='foreignkey')
        batch_op.drop_column('convertido')
        batch_op.drop_column('client_id')
        batch_op.create_foreign_key(None, 'orders', ['pedido_id'], ['id'])


def downgrade():
    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('client_id', sa.INTEGER(), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('convertido', sa.BOOLEAN(), autoincrement=False, nullable=True))

    op.execute("""
        UPDATE quotes
        SET client_id = (SELECT id FROM clients LIMIT 1)
        WHERE client_id IS NULL
    """)

    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.alter_column('client_id', nullable=False)

    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key('quotes_client_id_fkey', 'clients', ['client_id'], ['id'])
        batch_op.drop_column('pedido_id')
        batch_op.drop_column('status')
        batch_op.drop_column('cliente_telefone')
        batch_op.drop_column('cliente_nome')
