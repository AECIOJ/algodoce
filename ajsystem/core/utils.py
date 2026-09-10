"""Helpers genéricos de formatação/utilidade do framework.

Reutilizados por templates (filtros Jinja) e pelo motor de listagem/formulário.
Não dependem de modelos nem da aplicação host.
"""
import re
from datetime import datetime, timedelta

# Formatação/parse de máscara, número, moeda, data, transforms e validadores
# centralizados em `core/formats.py` (ver lá). Re-export para compat.
from ajsystem.core.formats import (  # noqa: F401
    parse_brl, fmt_id, fmt_brl, _fmt_number, normalize_currency, currency_symbol,
    fmt_money, fmt_percent, fmt_num, fmt_zero, fmt_date, fmt_zero_int,
    fmt_datetime, _title_case, apply_transform,
    mask_strip, fmt_mask_cmd, parse_mask_commands,
)
from ajsystem.defs.constants import CONECTORES, CURRENCY, DEFAULT_CURRENCY  # noqa: F401


def as_options(items):
    """Converte um iterável em dict de opções {valor: rótulo} idênticos
    para fields `LIST` (ex.: ['Kg', 'G'] -> {'Kg': 'Kg', 'G': 'G'})."""
    return {i: i for i in items}


def deep_attr(obj, path):
    if obj is None:
        return None
    for part in path.split('.'):
        if obj is None:
            return None
        try:
            obj = getattr(obj, part)
        except AttributeError:
            try:
                obj = obj[part]
            except (TypeError, KeyError, IndexError):
                return None
    return obj


def field_value(field, item):
    """Valor de um campo para `item`: acesso aninhado pelo nome."""
    return deep_attr(item, getattr(field, 'name', '') or '')


def divide(a, b):
    """Divisão segura: retorna 0 quando `b` é nulo/zero, evitando
    `ZeroDivisionError`."""
    if not b:
        return 0
    try:
        return a / b
    except (TypeError, ValueError):
        return 0


def add_dias(dta, dias):
    """Soma `dias` a uma data/hora, ignorando fuso. Retorna o mesmo tipo:
    `datetime` in → `datetime`, `date` in → `date`. `dias` nulo/0 é tratado
    como 0; `dta` nulo/ausente → `None`."""
    if dta is None:
        return None
    try:
        dias = int(dias or 0)
    except (TypeError, ValueError):
        dias = 0
    ref = dta
    if isinstance(ref, datetime) and ref.tzinfo is not None:
        ref = ref.replace(tzinfo=None)
    return ref + timedelta(days=dias)


def calc_value(calc, item):
    """Valor de um campo `calc` (virtual, não persistido) para `item`.

    - callable → `calc(item)`;
    - string → expressão aritmética avaliada com namespace restrito aos
      atributos de `item` (mesmo padrão do `_apply_aggs`).
    """
    if callable(calc):
        return calc(item)
    if not isinstance(calc, str):
        return None
    names = set(re.findall(r'[A-Za-z_][A-Za-z0-9_]*', calc or ''))
    ns = {n: (getattr(item, n, None) or 0) for n in names}
    ns['divide'] = divide
    try:
        return eval(calc, {'__builtins__': {}}, ns)
    except Exception:
        return None


def item_ref(item, siblings):
    """Identificador curto do registro para cabeçalhos de coluna (tabela
    transposta): usa a(s) coluna(s) da chave primária que variam entre os
    itens irmãos. Ex.: linha filha usa a FK para o pai; item de linha usa o
    próprio `id`. Retorna None quando não há como identificar (item novo/sem
    pk)."""
    if item is None:
        return None
    if isinstance(item, dict):
        return item.get('id')
    try:
        cols = list(item.__table__.primary_key.columns)
    except Exception:
        return getattr(item, 'id', None) or None
    if not cols:
        return getattr(item, 'id', None) or None
    varying = []
    for c in cols:
        vals = {getattr(i, c.name, None) for i in siblings}
        if len(vals) > 1:
            varying.append(c.name)
    names = varying or [c.name for c in cols]
    vals = [getattr(item, n, None) for n in names]
    vals = [v for v in vals if v is not None]
    return '-'.join(str(v) for v in vals) if vals else None


def preco_unit(valor, qtd):
    if not valor:
        return 0
    if not qtd:
        return float(valor)
    return float(valor) / float(qtd)


def query_label(cfg, key):
    """Rótulo padrão de uma Query: `label` explícito ou nome da chave."""
    if cfg is None:
        return _title_case(key) if key else ''
    label = cfg.get('label')
    if label:
        return label
    return _title_case(key) if key else ''


def list_table(valores: dict):
    """Cria uma CTE SQL (colunas `codigo`/`descricao`) a partir de um dict
    de valores, para uso em joins de listas de referência."""
    from sqlalchemy import select, union_all, literal
    ctes = [
        select(literal(k).label('codigo'), literal(v).label('descricao'))
        for k, v in valores.items()
    ]
    return union_all(*ctes).cte('list_table')
