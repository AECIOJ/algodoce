"""Catálogo de máscaras e formatação numérica do app.

Gêmeo de `app/extends/buttons.py`/`inputs.py`: o framework entrega os defaults
(`ajsystem.defs.masks`, em inglês) e o app define os seus aqui. Mudar uma
máscara neste arquivo reflete em todo o app.

Uso nas Entities/Schemas — importe o **nome**:

    from app.extends.masks import MVALOR
    Entity = {'valor': {'type': 'NUM', 'mask': MVALOR}, ...}

  - `DECIMAL`/`THOUSAND` — separadores de saída (pt-BR: `,`/`.`).
  - `MONEY`/`DEFAULT_MONEY` — moedas por id ISO e a moeda-base.
  - `MCPF`/`MCNPJ`/`MCEP`/`MPLACA`/`MTEL` — documentos (`@R` = não grava
    separadores no banco).
  - `MVALOR` — máscara de valor (canônica em inglês; o motor troca pelos
    `DECIMAL`/`THOUSAND`). Sem símbolo de moeda: em relatório o `R$` vai no
    rótulo da coluna, e repeti-lo em cada célula polui a leitura — ainda mais
    com a grade CPI, onde 3 caracteres a mais numerejam meia coluna.
"""

# ── Formatação (pt-BR) ───────────────────────────────────────────────────────
DECIMAL = ','
THOUSAND = '.'

# ── Moedas ───────────────────────────────────────────────────────────────────
MONEY = {'BRL': 'R$', 'USD': '$', 'EUR': '€'}
DEFAULT_MONEY = 'BRL'

# ── Documentos (texto; `@R` remove separadores no save) ──────────────────────
MCPF = '@R 999.999.999-99'
MCNPJ = '@R 99.999.999/9999-99'
MCEP = '@R 99999-999'
MPLACA = '@R AAA-9A99'
MTEL = '@R (99) 99999-9999'

# ── Valor (numérico canônico) ────────────────────────────────────────────────
MVALOR = '999,999.99'


# Catálogo efetivo consumido por `defs.masks.definir_masks` (merge do framework).
# Derivado no próprio import: toda constante (nome maiúsculo) do arquivo entra.
from ajsystem.defs.masks import collect_mask_catalog as _collect_masks
Masks = _collect_masks(globals())
