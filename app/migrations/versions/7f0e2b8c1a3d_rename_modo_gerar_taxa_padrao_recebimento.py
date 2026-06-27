"""rename modo→gerar, taxa_padrao→taxa_recebimento

Revision ID: 7f0e2b8c1a3d
Revises: 132fb07696d9
Create Date: 2026-06-27 15:22:03.442912

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '7f0e2b8c1a3d'
down_revision = '132fb07696d9'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE forma_pagamento RENAME COLUMN modo TO gerar")
    op.execute("ALTER TABLE forma_pagamento RENAME COLUMN taxa_padrao TO taxa_recebimento")


def downgrade():
    op.execute("ALTER TABLE forma_pagamento RENAME COLUMN gerar TO modo")
    op.execute("ALTER TABLE forma_pagamento RENAME COLUMN taxa_recebimento TO taxa_padrao")
