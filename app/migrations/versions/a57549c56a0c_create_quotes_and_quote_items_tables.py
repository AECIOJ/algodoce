"""create quotes and quote_items tables

Revision ID: a57549c56a0c
Revises: 74207fa1b00f
Create Date: 2026-06-12 15:27:22.480516

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision = 'a57549c56a0c'
down_revision = '74207fa1b00f'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('quotes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('client_id', sa.Integer(), nullable=False),
    sa.Column('data_pedido', sa.DateTime(), nullable=False),
    sa.Column('total', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('convertido', sa.Boolean(), nullable=True),
    sa.Column('observacao', sa.Text(), nullable=True),
    sa.Column('evento_tipo', sa.String(length=30), nullable=True),
    sa.Column('evento_tema', sa.String(length=200), nullable=True),
    sa.Column('evento_complemento', sa.Text(), nullable=True),
    sa.Column('evento_data', sa.Date(), nullable=True),
    sa.Column('evento_hora', sa.Time(), nullable=True),
    sa.Column('evento_local', sa.String(length=200), nullable=True),
    sa.Column('evento_convidados', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('quote_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('quote_id', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('quantidade', sa.Integer(), nullable=False),
    sa.Column('preco_unitario', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('observacao', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    conn = op.get_bind()
    rows = conn.execute(
        text("SELECT id, client_id, data_pedido, total, observacao, "
             "evento_tipo, evento_tema, evento_complemento, evento_data, "
             "evento_hora, evento_local, evento_convidados "
             "FROM orders WHERE status = 'rascunho'")
    ).fetchall()

    for row in rows:
        conn.execute(
            text("INSERT INTO quotes (id, client_id, data_pedido, total, convertido, observacao, "
                 "evento_tipo, evento_tema, evento_complemento, evento_data, evento_hora, "
                 "evento_local, evento_convidados) "
                 "VALUES (:id, :client_id, :data_pedido, :total, false, :observacao, "
                 ":evento_tipo, :evento_tema, :evento_complemento, :evento_data, :evento_hora, "
                 ":evento_local, :evento_convidados)"),
            {"id": row[0], "client_id": row[1], "data_pedido": row[2],
             "total": row[3], "observacao": row[4],
             "evento_tipo": row[5], "evento_tema": row[6],
             "evento_complemento": row[7], "evento_data": row[8],
             "evento_hora": row[9], "evento_local": row[10],
             "evento_convidados": row[11]}
        )

        items = conn.execute(
            text("SELECT id, product_id, quantidade, preco_unitario, observacao "
                 "FROM order_items WHERE order_id = :oid"),
            {"oid": row[0]}
        ).fetchall()

        for item in items:
            conn.execute(
                text("INSERT INTO quote_items (id, quote_id, product_id, quantidade, "
                     "preco_unitario, observacao) "
                     "VALUES (:id, :quote_id, :product_id, :quantidade, "
                     ":preco_unitario, :observacao)"),
                {"id": item[0], "quote_id": row[0], "product_id": item[1],
                 "quantidade": item[2], "preco_unitario": item[3],
                 "observacao": item[4]}
            )

        conn.execute(
            text("DELETE FROM order_items WHERE order_id = :oid"),
            {"oid": row[0]}
        )

        conn.execute(
            text("DELETE FROM orders WHERE id = :id"),
            {"id": row[0]}
        )


def downgrade():
    conn = op.get_bind()
    quotes = conn.execute(
        text("SELECT * FROM quotes")
    ).fetchall()

    for q in quotes:
        conn.execute(
            text("INSERT INTO orders (id, client_id, data_pedido, total, status, observacao, "
                 "evento_tipo, evento_tema, evento_complemento, evento_data, evento_hora, "
                 "evento_local, evento_convidados) "
                 "VALUES (:id, :client_id, :data_pedido, :total, 'rascunho', :observacao, "
                 ":evento_tipo, :evento_tema, :evento_complemento, :evento_data, :evento_hora, "
                 ":evento_local, :evento_convidados)"),
            {"id": q[0], "client_id": q[1], "data_pedido": q[2],
             "total": q[3], "observacao": q[5],
             "evento_tipo": q[6], "evento_tema": q[7],
             "evento_complemento": q[8], "evento_data": q[9],
             "evento_hora": q[10], "evento_local": q[11],
             "evento_convidados": q[12]}
        )

        items = conn.execute(
            text("SELECT id, product_id, quantidade, preco_unitario, observacao "
                 "FROM quote_items WHERE quote_id = :qid"),
            {"qid": q[0]}
        ).fetchall()

        for item in items:
            conn.execute(
                text("INSERT INTO order_items (id, order_id, product_id, quantidade, "
                     "preco_unitario, observacao) "
                     "VALUES (:id, :order_id, :product_id, :quantidade, "
                     ":preco_unitario, :observacao)"),
                {"id": item[0], "order_id": q[0], "product_id": item[1],
                 "quantidade": item[2], "preco_unitario": item[3],
                 "observacao": item[4]}
            )

    op.drop_table('quote_items')
    op.drop_table('quotes')
