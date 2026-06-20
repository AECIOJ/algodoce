"""change producao.status to integer

Revision ID: f9e0d1c2b3a5
Revises: f8e9d0c1b2a4
Create Date: 2026-06-19 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'f9e0d1c2b3a5'
down_revision = 'f8e9d0c1b2a4'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE producao ALTER COLUMN status DROP DEFAULT")
    op.alter_column('producao', 'status',
        type_=sa.Integer(),
        existing_type=sa.String(20),
        postgresql_using="CASE WHEN status IN ('Executando', 'andamento') THEN 0 WHEN status = 'finalizado' THEN 9 ELSE 0 END",
    )
    op.execute("ALTER TABLE producao ALTER COLUMN status SET DEFAULT 0")


def downgrade():
    op.execute("ALTER TABLE producao ALTER COLUMN status DROP DEFAULT")
    op.alter_column('producao', 'status',
        type_=sa.String(20),
        existing_type=sa.Integer(),
        postgresql_using="CASE WHEN status = 0 THEN 'Executando' WHEN status = 9 THEN 'finalizado' ELSE 'Executando' END",
    )
    op.execute("ALTER TABLE producao ALTER COLUMN status SET DEFAULT 'Executando'")
