"""rename clients to conta add tipo

Revision ID: 77769f39bb34
Revises: 9a8b7c6d5e4f
Create Date: 2026-06-16 16:47:49.158694

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '77769f39bb34'
down_revision = '9a8b7c6d5e4f'
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table('clients', 'conta')
    op.execute(sa.text("ALTER SEQUENCE clients_id_seq RENAME TO conta_id_seq"))
    op.add_column('conta', sa.Column('tipo', sa.Integer(), server_default='0'))
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_constraint('orders_client_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key('orders_client_id_fkey', 'conta', ['client_id'], ['id'])


def downgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_constraint('orders_client_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key('orders_client_id_fkey', 'clients', ['client_id'], ['id'])
    op.execute(sa.text("ALTER SEQUENCE conta_id_seq RENAME TO clients_id_seq"))
    op.rename_table('conta', 'clients')
    op.drop_column('conta', 'tipo')
