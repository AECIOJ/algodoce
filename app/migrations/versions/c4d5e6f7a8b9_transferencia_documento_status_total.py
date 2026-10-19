"""transferencia: documento no cabeçalho, status por código, total property

Três mudanças na mesma tabela `transferencias`:

- **`documento` sobe para o cabeçalho.** A transferência é um documento com
  identificação própria; o `documento` vivia só em `movimentos`, obrigava a
  repetir em cada lançamento e não tinha onde nascer numa linha nova. As
  linhas continuam com o campo (o valor é herdado, e editável).

- **`status` vira código (0/1/9), como as demais entidades.** Era
  `varchar(20)` ('Editando'/'Pendente'/'Fechada'). O backfill recalcula pelas
  linhas — não pelo texto e nem pela coluna `total`, que morre logo abaixo e
  nunca foi escrita (a transferência de teste tinha duas linhas de 250 e
  `total = 0.00` por acaso, então o status mentia).

- **`total` sai da tabela.** Vira property `sum(l.valor_assinado)`: os
  lançamentos são lançados pelo form e nada recalculava a coluna. Mesmo motivo
  e mesma solução de `b7c9d0e1f2a3` no `orcamentos.total`.

Revision ID: c4d5e6f7a8b9
Revises: b7c9d0e1f2a3
Create Date: 2026-10-15
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4d5e6f7a8b9'
down_revision = 'b7c9d0e1f2a3'
branch_labels = None
depends_on = None


_BACKFILL_STATUS = """
    UPDATE transferencias t SET status = CASE
        WHEN NOT EXISTS (
            SELECT 1 FROM movimentos m WHERE m.transferencia_id = t.id
        ) THEN 0
        WHEN ABS(COALESCE((
            SELECT SUM(CASE WHEN m.tipo = 'E' THEN m.valor ELSE -m.valor END)
            FROM movimentos m WHERE m.transferencia_id = t.id
        ), 0)) > 0.005 THEN 1
        ELSE 9
    END
"""


def upgrade():
    with op.batch_alter_table('transferencias', schema=None) as batch_op:
        batch_op.add_column(sa.Column('documento', sa.String(50), nullable=True))

    # varchar(20) → integer: o USING traduz o texto já gravado, para a coluna
    # não ficar inválida no meio (o UPDATE seguinte é quem manda no valor). O
    # default antigo sai antes — `'Editando'` não é conversível, e o Postgres
    # tenta casá-lo com o tipo novo.
    with op.batch_alter_table('transferencias', schema=None) as batch_op:
        batch_op.alter_column('status', server_default=None)

    with op.batch_alter_table('transferencias', schema=None) as batch_op:
        batch_op.alter_column('status', existing_type=sa.String(20),
                              type_=sa.Integer(), existing_nullable=False,
                              existing_server_default=None,
                              postgresql_using="CASE status "
                                               "WHEN 'Pendente' THEN 1 "
                                               "WHEN 'Fechada' THEN 9 ELSE 0 END",
                              server_default='0')
    op.execute(_BACKFILL_STATUS)

    with op.batch_alter_table('transferencias', schema=None) as batch_op:
        batch_op.drop_column('total')


def downgrade():
    with op.batch_alter_table('transferencias', schema=None) as batch_op:
        batch_op.add_column(sa.Column('total', sa.Numeric(12, 2), nullable=False,
                                      server_default='0'))
    # Recalcula a coluna a partir dos lançamentos, senão ela volta zerada.
    op.execute("""
        UPDATE transferencias t SET total = (
            SELECT COALESCE(SUM(
                CASE WHEN m.tipo = 'E' THEN m.valor ELSE -m.valor END), 0)
            FROM movimentos m WHERE m.transferencia_id = t.id
        )
    """)

    with op.batch_alter_table('transferencias', schema=None) as batch_op:
        batch_op.alter_column('status', server_default=None)

    with op.batch_alter_table('transferencias', schema=None) as batch_op:
        batch_op.alter_column('status', existing_type=sa.Integer(),
                              type_=sa.String(20), existing_nullable=False,
                              existing_server_default=None,
                              postgresql_using="CASE status "
                                               "WHEN 1 THEN 'Pendente' "
                                               "WHEN 9 THEN 'Fechada' "
                                               "ELSE 'Editando' END",
                              server_default='Editando')