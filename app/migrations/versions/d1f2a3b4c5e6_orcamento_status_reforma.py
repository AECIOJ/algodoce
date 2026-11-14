"""orcamento status reforma: 7->5, data_rejeicao, backfill expirados

Revision ID: d1f2a3b4c5e6
Revises: c0e1f2a3b4d5
Create Date: 2026-11-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd1f2a3b4c5e6'
down_revision = 'c0e1f2a3b4d5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('orcamentos',
                  sa.Column('data_rejeicao', sa.Date(), nullable=True))
    conn = op.get_bind()
    # Remap: 7 (Expirado) deixa de existir -> 5
    conn.execute(sa.text("UPDATE orcamentos SET status = 5 WHERE status = 7"))
    # Correção de legado: expirados "perdidos" (0/1/6, sem pedido, validade vencida)
    conn.execute(sa.text("""
        UPDATE orcamentos SET status = 5
        WHERE status IN (0, 1, 6) AND pedido_id IS NULL
          AND (COALESCE(data_renovacao, data)
               + make_interval(days => COALESCE(validade, 3))) < now()
    """))


def downgrade():
    conn = op.get_bind()
    # Reversão aproximada: 5 -> 7 (não distingue backfill de remap)
    conn.execute(sa.text("UPDATE orcamentos SET status = 7 WHERE status = 5"))
    op.drop_column('orcamentos', 'data_rejeicao')
