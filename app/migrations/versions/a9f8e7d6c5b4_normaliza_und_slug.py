"""normaliza vocabulário `und` para chaves slug (minúsculas, sem acento)

Revision ID: a9f8e7d6c5b4
Revises: d2e3f4a5b6c7
Create Date: 2026-09-23

`UND_INSUMO` passou a ser gerado por `as_options(...)` (chaves derivadas do
rótulo: sem acento e com `_` no lugar de espaço). Atualiza os valores já
gravados nas colunas `und`:

    'Kg' -> 'kg', 'Un' -> 'un', 'Colher_cha' -> 'colher_de_cha', ...
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'a9f8e7d6c5b4'
down_revision = 'd2e3f4a5b6c7'
branch_labels = None
depends_on = None

_UP = {
    'Kg': 'kg', 'kg': 'kg',
    'G': 'g', 'g': 'g',
    'L': 'l', 'l': 'l',
    'Ml': 'ml', 'ml': 'ml',
    'Un': 'un', 'un': 'un',
    'Colher_cha': 'colher_de_cha', 'colher_cha': 'colher_de_cha',
    'Colher_sopa': 'colher_de_sopa', 'colher_sopa': 'colher_de_sopa',
    'Xicara': 'xicara', 'xicara': 'xicara',
    'Pitada': 'pitada', 'pitada': 'pitada',
}

_DOWN = {
    'kg': 'Kg',
    'g': 'G',
    'l': 'L',
    'ml': 'Ml',
    'un': 'Un',
    'colher_de_cha': 'Colher_cha',
    'colher_de_sopa': 'Colher_sopa',
    'xicara': 'Xicara',
    'pitada': 'Pitada',
}

_TABLES = ('insumos', 'produto_insumos', 'insumo_conversoes', 'producao_insumos')


def _aplicar(mapping, tabelas):
    for table in tabelas:
        for antigo, novo in mapping.items():
            op.execute(
                f"UPDATE {table} SET und = '{novo}' WHERE und = '{antigo}'"
            )


def upgrade():
    _aplicar(_UP, _TABLES)


def downgrade():
    _aplicar(_DOWN, _TABLES)