"""
FILTER_* — Constantes de configuração de filtro do framework.

Cada FILTER_* define type + modes (lista de tuplas [valor, label]).
Usado no Motor via build_filter_config() e no front-end JS.

Uso em definições de Field:
  from app.ajsystem.defs.filters import FILTER_NUMBER, FILTER_TEXT, FILTER_SELECT

  Field(name='valor', input='number', filter=FILTER_NUMBER)
  Field(name='status', input='select', filter={**FILTER_SELECT, 'options': STATUS})
"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  FILTER_* — Tipos de filtro
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FILTER_TEXT = {
    'type': 'text',
    'modes': [
        ('igual',    'Igual a'),
        ('contains', 'Contém'),
        ('starts',   'Começa'),
    ],
}

FILTER_NUMBER = {
    'type': 'number',
    'modes': [
        ('igual',       'Igual a'),
        ('entre',       'Entre'),
        ('maior_que',   'Maior que'),
        ('maior_igual', 'Maior ou igual a'),
        ('menor_que',   'Menor que'),
        ('menor_igual', 'Menor ou igual a'),
    ],
}

FILTER_DATE = {
    'type': 'date',
    'modes': [
        ('hoje',           'Hoje'),
        ('periodo',        'Período'),
        ('ontem',          'Ontem'),
        ('ultimos_7_dias', 'Últimos 7 dias'),
        ('mes',            'Mês'),
        ('mes_atual',      'Mês Atual'),
        ('mes_anterior',   'Mês Anterior'),
        ('ano',            'Ano'),
        ('ano_atual',      'Ano Atual'),
        ('a_partir_de',    'A partir de'),
        ('ate_a_data_de',  'Até a data de'),
    ],
}

FILTER_BOOLEAN = {
    'type': 'boolean',
    'modes': [
        ('',      'Todos'),
        ('true',  'Sim'),
        ('false', 'Não'),
    ],
}

FILTER_SELECT = {
    'type': 'select',
}

# Backward-compat aliases (old MODE_* → FILTER_*)
MODE_TEXT = FILTER_TEXT
MODE_NUMBER = FILTER_NUMBER
MODE_DATE = FILTER_DATE
MODE_BOOLEAN = FILTER_BOOLEAN
MODE_SELECT = FILTER_SELECT
