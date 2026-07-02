"""rename forma_pagamento to carteira

Revision ID: 5096816c1660
Revises: efe49ca52245
Create Date: 2026-06-30 10:06:48.282880

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "5096816c1660"
down_revision = "efe49ca52245"
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table("forma_pagamento", "carteira")
    op.execute("ALTER SEQUENCE forma_pagamento_id_seq RENAME TO carteira_id_seq")

    for table in ("compras", "orders", "previsao", "quotes"):
        fk_name = f"{table}_forma_pagamento_id_fkey"
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_constraint(fk_name, type_="foreignkey")
        op.alter_column(table, "forma_pagamento_id", new_column_name="carteira_id")
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.create_foreign_key(None, "carteira", ["carteira_id"], ["id"])


def downgrade():
    op.rename_table("carteira", "forma_pagamento")
    op.execute("ALTER SEQUENCE carteira_id_seq RENAME TO forma_pagamento_id_seq")

    for table in ("compras", "orders", "previsao", "quotes"):
        fk_name = f"{table}_carteira_id_fkey"
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_constraint(fk_name, type_="foreignkey")
        op.alter_column(table, "carteira_id", new_column_name="forma_pagamento_id")
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.create_foreign_key(None, "forma_pagamento", ["forma_pagamento_id"], ["id"])
