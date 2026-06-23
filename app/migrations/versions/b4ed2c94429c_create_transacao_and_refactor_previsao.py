"""create transacao and refactor previsao

Revision ID: b4ed2c94429c
Revises: 8597fd57639d
Create Date: 2026-06-22 10:15:46.560596

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b4ed2c94429c'
down_revision = '8597fd57639d'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # 1. Create transacao table
    op.create_table('transacao',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('data', sa.Date(), nullable=False),
        sa.Column('tipo', sa.String(1), nullable=False),
        sa.Column('conta_id', sa.Integer(), sa.ForeignKey('conta.id'), nullable=True),
        sa.Column('rubrica_id', sa.Integer(), sa.ForeignKey('rubrica.id'), nullable=True),
        sa.Column('fatura', sa.String(50), nullable=True),
        sa.Column('valor', sa.Numeric(12, 2), nullable=False),
        sa.Column('historico', sa.Text(), nullable=True),
        sa.Column('cancelado', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # 2. Create new previsao (detail) table
    op.create_table('previsao',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transacao_id', sa.Integer(), sa.ForeignKey('transacao.id'), nullable=False),
        sa.Column('documento', sa.String(50), nullable=True),
        sa.Column('vencimento', sa.Date(), nullable=False),
        sa.Column('previsto', sa.Numeric(12, 2), nullable=False),
        sa.Column('realizado', sa.Numeric(12, 2), nullable=True),
        sa.Column('variacao', sa.Numeric(12, 2), nullable=True, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
    )

    # 3. Migrate data from old previsoes to transacao + previsao
    rows = conn.execute(
        sa.text("SELECT * FROM previsoes ORDER BY id")
    ).fetchall()

    for row in rows:
        r = conn.execute(
            sa.text(
                "INSERT INTO transacao (data, tipo, conta_id, rubrica_id, "
                "fatura, valor, historico, cancelado) "
                "VALUES (:data, :tipo, :conta_id, :rubrica_id, "
                "NULL, :valor, :historico, :cancelado) RETURNING id"
            ),
            {
                "data": row.data,
                "tipo": row.tipo,
                "conta_id": row.conta_id,
                "rubrica_id": row.rubrica_id,
                "valor": float(row.previsto),
                "historico": row.historico,
                "cancelado": row.cancelado,
            }
        ).scalar()

        conn.execute(
            sa.text(
                "INSERT INTO previsao (transacao_id, documento, vencimento, "
                "previsto, realizado, variacao) "
                "VALUES (:tid, :doc, :venc, :prev, :real, :var)"
            ),
            {
                "tid": r,
                "doc": row.documento,
                "venc": row.vencimento,
                "prev": float(row.previsto),
                "real": float(row.realizado) if row.realizado else None,
                "var": float(row.variacao) if row.variacao else 0,
            }
        )

    # 4. Drop old table
    op.drop_table('previsoes')


def downgrade():
    op.create_table('previsoes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('data', sa.Date(), nullable=False),
        sa.Column('tipo', sa.String(1), nullable=False),
        sa.Column('conta_id', sa.Integer(), sa.ForeignKey('conta.id'), nullable=True),
        sa.Column('documento', sa.String(50), nullable=True),
        sa.Column('vencimento', sa.Date(), nullable=False),
        sa.Column('previsto', sa.Numeric(12, 2), nullable=False),
        sa.Column('rubrica_id', sa.Integer(), sa.ForeignKey('rubrica.id'), nullable=True),
        sa.Column('status', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cancelado', sa.Date(), nullable=True),
        sa.Column('historico', sa.Text(), nullable=True),
        sa.Column('realizado', sa.Numeric(12, 2), nullable=True),
        sa.Column('variacao', sa.Numeric(12, 2), nullable=True, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
    )

    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT t.*, p.id AS pid, p.documento, p.vencimento, "
                "p.previsto, p.realizado, p.variacao "
                "FROM transacao t JOIN previsao p ON p.transacao_id = t.id "
                "ORDER BY p.id")
    ).fetchall()

    for row in rows:
        conn.execute(
            sa.text(
                "INSERT INTO previsoes (data, tipo, conta_id, documento, "
                "vencimento, previsto, rubrica_id, cancelado, historico, "
                "realizado, variacao) "
                "VALUES (:data, :tipo, :conta_id, :doc, :venc, :prev, "
                ":rubrica_id, :cancelado, :historico, :real, :var)"
            ),
            {
                "data": row.data,
                "tipo": row.tipo,
                "conta_id": row.conta_id,
                "doc": row.documento,
                "venc": row.vencimento,
                "prev": float(row.previsto),
                "rubrica_id": row.rubrica_id,
                "cancelado": row.cancelado,
                "historico": row.historico,
                "real": float(row.realizado) if row.realizado else None,
                "var": float(row.variacao) if row.variacao else 0,
            }
        )

    op.drop_table('previsao')
    op.drop_table('transacao')
