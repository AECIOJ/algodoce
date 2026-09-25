"""previsao: carteira_id -> recurso_id (FK para recurso.id)

Revision ID: d2e3f4a5b6c7
Revises: c1a2b3d4e5f6
Create Date: 2026-09-22

Renomeia `previsao.carteira_id` (esquema de pagamento) para `recurso_id`
(caixa/fonte), alinhando com `movimento.recurso_id`. Os valores antigos
não podem ser mapeados de forma confiável (carteira != recurso) e são
zerados.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd2e3f4a5b6c7'
down_revision = 'c1a2b3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE previsao DROP CONSTRAINT IF EXISTS previsao_carteira_id_fkey")
    op.execute("UPDATE previsao SET carteira_id = NULL WHERE carteira_id IS NOT NULL")

    with op.batch_alter_table('previsao', schema=None) as batch_op:
        batch_op.alter_column('carteira_id', new_column_name='recurso_id')

    with op.batch_alter_table('previsao', schema=None) as batch_op:
        batch_op.create_foreign_key(None, 'recurso', ['recurso_id'], ['id'])


def downgrade():
    op.execute("ALTER TABLE previsao DROP CONSTRAINT IF EXISTS previsao_recurso_id_fkey")
    op.execute("UPDATE previsao SET recurso_id = NULL WHERE recurso_id IS NOT NULL")

    with op.batch_alter_table('previsao', schema=None) as batch_op:
        batch_op.alter_column('recurso_id', new_column_name='carteira_id')

    with op.batch_alter_table('previsao', schema=None) as batch_op:
        batch_op.create_foreign_key(None, 'carteira', ['carteira_id'], ['id'])