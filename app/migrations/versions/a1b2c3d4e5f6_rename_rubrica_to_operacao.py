"""rename rubrica to operacao

Revision ID: a1b2c3d4e5f6
Revises: 2c8fe2a4c13b
Create Date: 2026-07-13 10:00:00.000000

"""
from alembic import op


revision = 'a1b2c3d4e5f6'
down_revision = '2c8fe2a4c13b'
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table("rubrica", "operacao")
    op.execute("ALTER SEQUENCE rubrica_id_seq RENAME TO operacao_id_seq")

    for table in ("transacao", "movto"):
        fk_name = f"{table}_rubrica_id_fkey"
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_constraint(fk_name, type_="foreignkey")
        op.alter_column(table, "rubrica_id", new_column_name="operacao_id")
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.create_foreign_key(None, "operacao", ["operacao_id"], ["id"])


def downgrade():
    op.rename_table("operacao", "rubrica")
    op.execute("ALTER SEQUENCE operacao_id_seq RENAME TO rubrica_id_seq")

    for table in ("transacao", "movto"):
        fk_name = f"{table}_operacao_id_fkey"
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_constraint(fk_name, type_="foreignkey")
        op.alter_column(table, "operacao_id", new_column_name="rubrica_id")
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.create_foreign_key(None, "rubrica", ["rubrica_id"], ["id"])
