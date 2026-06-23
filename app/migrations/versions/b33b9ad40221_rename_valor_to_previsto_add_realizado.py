"""rename valor to previsto, add realizado

Revision ID: b33b9ad40221
Revises: aaa5b6c7d8e9
Create Date: 2026-06-22 09:17:36.159442

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b33b9ad40221'
down_revision = 'aaa5b6c7d8e9'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('previsoes', 'valor', new_column_name='previsto')
    op.add_column('previsoes', sa.Column('realizado', sa.Numeric(precision=12, scale=2), nullable=True))


def downgrade():
    op.drop_column('previsoes', 'realizado')
    op.alter_column('previsoes', 'previsto', new_column_name='valor')
