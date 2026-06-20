"""remove etapas table, add producao_0/1/2 columns

Revision ID: faeb0c1d2b3a6
Revises: f9e0d1c2b3a5
Create Date: 2026-06-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'faeb0c1d2b3a6'
down_revision = 'f9e0d1c2b3a5'
branch_labels = None
depends_on = None


def upgrade():
    # Drop FK constraints if they exist
    op.execute('ALTER TABLE product_ingredients DROP CONSTRAINT IF EXISTS fk_pi_etapa_id')
    op.execute('ALTER TABLE product_ingredients DROP CONSTRAINT IF EXISTS product_ingredients_etapa_id_fkey')
    op.execute('ALTER TABLE producao_produtos DROP CONSTRAINT IF EXISTS fk_pp_etapa_atual')
    op.execute('ALTER TABLE producao_produtos DROP CONSTRAINT IF EXISTS producao_produtos_etapa_atual_id_fkey')

    # Add producao_0 column (nullable first)
    op.add_column('producao_produtos', sa.Column('producao_0', sa.Integer(), nullable=True))

    # Migrate data: copy producao_0 = COALESCE(produzido, 0)
    op.execute('UPDATE producao_produtos SET producao_0 = COALESCE(produzido, 0)')

    # Add remaining columns with default
    op.add_column('producao_produtos', sa.Column('producao_1', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('producao_produtos', sa.Column('producao_2', sa.Integer(), nullable=False, server_default='0'))

    # Make producao_0 non-nullable with default
    op.alter_column('producao_produtos', 'producao_0',
                    existing_type=sa.Integer(),
                    nullable=False,
                    server_default='0')

    # Drop old columns
    op.drop_column('producao_produtos', 'produzido')
    op.drop_column('producao_produtos', 'etapa_atual_id')

    # Drop etapas table
    op.execute('DROP TABLE IF EXISTS etapas CASCADE')


def downgrade():
    # Recreate etapas table
    op.create_table('etapas',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('nome', sa.String(100), nullable=False),
        sa.Column('ordem', sa.Integer(), nullable=False),
    )

    # Restore old columns
    op.add_column('producao_produtos', sa.Column('produzido', sa.Integer(), nullable=True))
    op.add_column('producao_produtos', sa.Column('etapa_atual_id', sa.Integer(), nullable=True))

    # Restore data: producao_0 → producao
    op.execute('UPDATE producao_produtos SET producao = COALESCE(producao_0, 0)')

    # Drop new columns
    op.drop_column('producao_produtos', 'producao_0')
    op.drop_column('producao_produtos', 'producao_1')
    op.drop_column('producao_produtos', 'producao_2')

    # Restore FKs
    op.execute('ALTER TABLE product_ingredients ADD CONSTRAINT fk_pi_etapa_id FOREIGN KEY (etapa_id) REFERENCES etapas(id)')
    op.create_foreign_key('fk_pp_etapa_atual', 'producao_produtos', 'etapas', ['etapa_atual_id'], ['id'])
