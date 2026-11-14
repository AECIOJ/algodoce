"""pedido backfill: status 8 sem data_cancelado volta ao derivado

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-11-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3a4b5c6d7e8'
down_revision = 'e2f3a4b5c6d7'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # Corrige legado: status 8 (Cancelado) sem data de cancelamento → Pendente
    conn.execute(sa.text("""
        UPDATE pedidos SET status = 0
        WHERE status = 8 AND data_cancelado IS NULL
    """))


def downgrade():
    conn = op.get_bind()
    # Reversão aproximada: não há como saber a data original, mantém 0
    pass
