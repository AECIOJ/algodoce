"""add event fields to Order, nullable preco to OrderItem, observacao to OrderItem

Revision ID: abc123def456
Revises: d3c1b5f7e902
Create Date: 2026-06-10 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "abc123def456"
down_revision = "d3c1b5f7e902"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(sa.Column("evento_tipo", sa.String(30), nullable=True))
        batch_op.add_column(sa.Column("evento_complemento", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("evento_data", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("evento_hora", sa.Time(), nullable=True))
        batch_op.add_column(sa.Column("evento_local", sa.String(200), nullable=True))
        batch_op.add_column(sa.Column("evento_convidados", sa.Integer(), nullable=True))
        batch_op.alter_column("total", existing_type=sa.Numeric(10, 2), nullable=True)
        batch_op.alter_column("data_entrega", existing_type=sa.Date(), nullable=True)
        batch_op.alter_column("status", existing_type=sa.String(20),
                              nullable=False, server_default="rascunho")

    with op.batch_alter_table("order_items") as batch_op:
        batch_op.add_column(sa.Column("observacao", sa.Text(), nullable=True))
        batch_op.alter_column("preco_unitario", existing_type=sa.Numeric(10, 2),
                              nullable=True)


def downgrade():
    with op.batch_alter_table("order_items") as batch_op:
        batch_op.drop_column("observacao")
        batch_op.alter_column("preco_unitario", existing_type=sa.Numeric(10, 2),
                              nullable=False)

    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_column("evento_convidados")
        batch_op.drop_column("evento_local")
        batch_op.drop_column("evento_hora")
        batch_op.drop_column("evento_data")
        batch_op.drop_column("evento_complemento")
        batch_op.drop_column("evento_tipo")
        batch_op.alter_column("status", existing_type=sa.String(20),
                              nullable=False, server_default="pendente")
