"""create events table and migrate event data

Revision ID: d536bf4d6886
Revises: 1834e684b61b
Create Date: 2026-06-13 10:53:16.270273

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd536bf4d6886'
down_revision = '1834e684b61b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quote_id', sa.Integer(), nullable=True),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('tipo', sa.String(length=30), nullable=True),
        sa.Column('tema', sa.String(length=200), nullable=True),
        sa.Column('complemento', sa.Text(), nullable=True),
        sa.Column('data', sa.Date(), nullable=True),
        sa.Column('hora', sa.Time(), nullable=True),
        sa.Column('local', sa.String(length=200), nullable=True),
        sa.Column('convidados', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id'),
        sa.UniqueConstraint('quote_id')
    )

    # ---- data migration ----
    conn = op.get_bind()

    conn.execute(sa.text("""
        INSERT INTO events (quote_id, order_id, tipo, tema, complemento, data, hora, local, convidados)
        SELECT q.id, q.pedido_id, q.evento_tipo, q.evento_tema, q.evento_complemento,
               q.evento_data, q.evento_hora, q.evento_local, q.evento_convidados
        FROM quotes q
        WHERE COALESCE(q.evento_tipo, q.evento_tema, q.evento_complemento,
                       q.evento_data::text, q.evento_hora::text, q.evento_local,
                       q.evento_convidados::text) IS NOT NULL
    """))

    conn.execute(sa.text("""
        UPDATE events e
        SET tipo = o.evento_tipo,
            tema = o.evento_tema,
            complemento = o.evento_complemento,
            data = o.evento_data,
            hora = o.evento_hora,
            local = o.evento_local,
            convidados = o.evento_convidados
        FROM orders o
        WHERE e.order_id = o.id
          AND (o.evento_tipo IS NOT NULL
            OR o.evento_tema IS NOT NULL
            OR o.evento_complemento IS NOT NULL
            OR o.evento_data IS NOT NULL
            OR o.evento_hora IS NOT NULL
            OR o.evento_local IS NOT NULL
            OR o.evento_convidados IS NOT NULL)
    """))

    conn.execute(sa.text("""
        INSERT INTO events (order_id, tipo, tema, complemento, data, hora, local, convidados)
        SELECT o.id, o.evento_tipo, o.evento_tema, o.evento_complemento,
               o.evento_data, o.evento_hora, o.evento_local, o.evento_convidados
        FROM orders o
        WHERE NOT EXISTS (SELECT 1 FROM events e WHERE e.order_id = o.id)
          AND (o.evento_tipo IS NOT NULL
            OR o.evento_tema IS NOT NULL
            OR o.evento_complemento IS NOT NULL
            OR o.evento_data IS NOT NULL
            OR o.evento_hora IS NOT NULL
            OR o.evento_local IS NOT NULL
            OR o.evento_convidados IS NOT NULL)
    """))

    # ---- drop old columns ----
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('evento_tema')
        batch_op.drop_column('evento_data')
        batch_op.drop_column('evento_complemento')
        batch_op.drop_column('evento_convidados')
        batch_op.drop_column('evento_local')
        batch_op.drop_column('evento_tipo')
        batch_op.drop_column('evento_hora')

    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.drop_column('evento_tema')
        batch_op.drop_column('evento_data')
        batch_op.drop_column('evento_complemento')
        batch_op.drop_column('evento_convidados')
        batch_op.drop_column('evento_local')
        batch_op.drop_column('evento_tipo')
        batch_op.drop_column('evento_hora')


def downgrade():
    # ---- restore old columns ----
    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('evento_hora', postgresql.TIME(), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('evento_tipo', sa.VARCHAR(length=30), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('evento_local', sa.VARCHAR(length=200), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('evento_convidados', sa.INTEGER(), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('evento_complemento', sa.TEXT(), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('evento_data', sa.DATE(), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('evento_tema', sa.VARCHAR(length=200), autoincrement=False, nullable=True))

    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('evento_hora', postgresql.TIME(), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('evento_tipo', sa.VARCHAR(length=30), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('evento_local', sa.VARCHAR(length=200), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('evento_convidados', sa.INTEGER(), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('evento_complemento', sa.TEXT(), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('evento_data', sa.DATE(), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('evento_tema', sa.VARCHAR(length=200), autoincrement=False, nullable=True))

    # ---- restore event data into old columns ----
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE quotes q
        SET evento_tipo = e.tipo, evento_tema = e.tema, evento_complemento = e.complemento,
            evento_data = e.data, evento_hora = e.hora, evento_local = e.local,
            evento_convidados = e.convidados
        FROM events e
        WHERE e.quote_id = q.id
    """))
    conn.execute(sa.text("""
        UPDATE orders o
        SET evento_tipo = e.tipo, evento_tema = e.tema, evento_complemento = e.complemento,
            evento_data = e.data, evento_hora = e.hora, evento_local = e.local,
            evento_convidados = e.convidados
        FROM events e
        WHERE e.order_id = o.id
    """))
    op.drop_table('events')
