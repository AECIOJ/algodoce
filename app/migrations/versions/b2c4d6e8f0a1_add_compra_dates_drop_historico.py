"""add compra date columns and drop compra_historico

Revision ID: b2c4d6e8f0a1
Revises: 8e4d2c6f9a17
Create Date: 2026-09-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c4d6e8f0a1'
down_revision = '8e4d2c6f9a17'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar colunas de data e observação à tabela compras
    with op.batch_alter_table('compras', schema=None) as batch_op:
        batch_op.add_column(sa.Column('pedido_em', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('compra_em', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('cancelado_em', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('recebido_em', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('devolvido_em', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('observacao', sa.Text(), nullable=True))

    # Migrar dados existentes de compra_historico para as novas colunas
    conn = op.get_bind()
    # Mapeamento de statusCompraHistorico → coluna na tabela compras
    status_map = {
        1: 'pedido_em',
        2: 'compra_em',
        6: 'cancelado_em',
        8: 'recebido_em',
        9: 'devolvido_em',
    }
    rows = conn.execute(sa.text(
        "SELECT compra_id, status, data, motivo FROM compra_historico"
    )).fetchall()
    for compra_id, status, data, motivo in rows:
        col = status_map.get(status)
        if col and data:
            conn.execute(
                sa.text(f"UPDATE compras SET {col} = :data WHERE id = :cid"),
                {'data': data, 'cid': compra_id},
            )
        if motivo:
            conn.execute(
                sa.text(
                    "UPDATE compras SET observacao = :motivo "
                    "WHERE id = :cid AND (observacao IS NULL OR observacao = '')"
                ),
                {'motivo': motivo, 'cid': compra_id},
            )

    # Remover tabela compra_historico
    op.drop_table('compra_historico')


def downgrade():
    # Recriar tabela compra_historico
    op.create_table(
        'compra_historico',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('compra_id', sa.Integer(), sa.ForeignKey('compras.id'), nullable=False),
        sa.Column('status', sa.Integer(), nullable=False),
        sa.Column('data', sa.Date(), nullable=False),
        sa.Column('usuario', sa.String(100), nullable=True),
        sa.Column('responsavel', sa.String(100), nullable=True),
        sa.Column('motivo', sa.Text(), nullable=True),
    )

    # Migrar dados de volta (data + motivo)
    conn = op.get_bind()
    col_to_status = {
        'pedido_em': 1, 'compra_em': 2, 'cancelado_em': 6,
        'recebido_em': 8, 'devolvido_em': 9,
    }
    for col, status in col_to_status.items():
        conn.execute(sa.text(
            f"INSERT INTO compra_historico (compra_id, status, data, motivo) "
            f"SELECT id, {status}, {col}, observacao FROM compras "
            f"WHERE {col} IS NOT NULL"
        ))

    # Remover colunas adicionadas
    with op.batch_alter_table('compras', schema=None) as batch_op:
        batch_op.drop_column('observacao')
        batch_op.drop_column('devolvido_em')
        batch_op.drop_column('recebido_em')
        batch_op.drop_column('cancelado_em')
        batch_op.drop_column('compra_em')
        batch_op.drop_column('pedido_em')
