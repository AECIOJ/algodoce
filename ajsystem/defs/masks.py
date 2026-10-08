"""Catálogo de máscaras e formatação numérica do framework (genérico, sem host).

Defaults em inglês (en-US): `DECIMAL='.'`, `THOUSAND=','`, `MONEY` com `$`.
O host sobrescreve `Masks` em `app/extends/masks.py` (mesmo merge de
`buttons`/`inputs`/`fonts`): `MASKS < Masks(app)`.

Chaves:
  - `DECIMAL`/`THOUSAND`  — separadores de saída (formatação numérica).
  - `MONEY`/`DEFAULT_MONEY` — catálogo de moedas por id ISO (`{'BRL': 'R$'}`)
    e a moeda-base (legados `1`/`True`/`'brl'` e `@M` sem id).
  - `MVALOR`, `MCPF`, `MCNPJ`, `MCEP`, `MPLACA`… — máscaras nomeadas. As
    numéricas são escritas no padrão canônico inglês e o motor troca pelos
    `DECIMAL`/`THOUSAND` na renderização.

Máscara numérica canônica: `0` = dígito com zero-pad, `9` = dígito opcional,
`,` = milhar (agrupa se presente), `.` = decimal (casas após o último `.`).
`@M(id)` = moeda (`@M(BRL) 999,999,999.99`); `@R` = remover separadores no save.
"""

# ── Formatação (default en-US) ───────────────────────────────────────────────
DECIMAL = '.'
THOUSAND = ','
MONEY = {'USD': '$'}
DEFAULT_MONEY = 'USD'

# Máscaras nomeadas (genéricas; o host adiciona as de domínio).
MVALOR = '@M(USD) 999,999,999.99'


def collect_mask_catalog(globals_dict, exclude=('MASKS', 'Masks')) -> dict:
    """Monta o catálogo de máscaras no próprio import do módulo.

    Toda constante de módulo (nome maiúsculo, valor `str`/`dict`, exceto o
    próprio dicionário e underscores) é entrada do catálogo, na ordem em que é
    declarada — adicionar um `M*` novo no arquivo não exige mexer no dict.
    """
    return {k: v for k, v in globals_dict.items()
            if k.isupper() and not k.startswith('_')
            and k not in exclude
            and isinstance(v, (str, dict))}


MASKS = collect_mask_catalog(globals(), exclude={'MASKS'})


def merge_masks(overrides=None) -> dict:
    """`MASKS` (framework) com o `Masks` do host por cima (`MONEY` = replace)."""
    cfg = dict(MASKS)
    for k, v in (overrides or {}).items():
        cfg[k] = v
    return cfg


def definir_masks(overrides=None) -> dict:
    """Aplica o catálogo efetivo nos renderizadores (`core/formats`)."""
    from ajsystem.core import formats
    cfg = merge_masks(overrides)
    formats.definir_formatacao(
        decimal=cfg['DECIMAL'],
        thousand=cfg['THOUSAND'],
        money=cfg['MONEY'],
        default_money=cfg['DEFAULT_MONEY'],
    )
    return cfg
