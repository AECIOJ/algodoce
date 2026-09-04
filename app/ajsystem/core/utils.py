"""Helpers genéricos de formatação/utilidade do framework.

Reutilizados por templates (filtros Jinja) e pelo motor de listagem/formulário.
Não dependem de modelos nem da aplicação host.
"""
import re
from datetime import datetime, timedelta

from app.ajsystem.defs.constants import CONECTORES, CURRENCY, DEFAULT_CURRENCY


def as_options(items):
    """Converte um iterável em dict de opções {valor: rótulo} idênticos
    para fields `LIST` (ex.: ['Kg', 'G'] -> {'Kg': 'Kg', 'G': 'G'})."""
    return {i: i for i in items}


def parse_brl(value):
    if not value:
        return None
    if ',' in value:
        return float(value.replace('.', '').replace(',', '.'))
    return float(value)


def fmt_id(value):
    if value is None:
        return '0'
    formatted = f'{value:,}'.replace(',', '.')
    return ('%7s' % formatted).replace(' ', '\u00A0')


def fmt_brl(value):
    """Filtro legado `brl` (sem símbolo; None → '0,00')."""
    if value is None:
        return '0,00'
    return _fmt_number(value, 'pt-BR')


def _fmt_number(value, locale):
    """Número com 2 decimais no agrupamento do locale (sem símbolo)."""
    if value is None:
        return '0,00' if locale == 'pt-BR' else '0.00'
    try:
        num = f'{float(value):,.2f}'
    except (TypeError, ValueError):
        return str(value)
    if locale == 'pt-BR':
        num = num.replace(',', 'X').replace('.', ',').replace('X', '.')
    return num


def normalize_currency(cur):
    """Normaliza a prop `Field.currency` para código de `CURRENCY`.

    `True`/`'brl'` legados e `1` → padrão; `0`/`None`/`False` → desligado
    (None); código desconhecido → desligado (nunca quebra, nunca mente
    símbolo). Retorna o código int ou None.
    """
    if cur is None or cur is False or cur == 0:
        return None
    if cur is True:
        return DEFAULT_CURRENCY
    if isinstance(cur, str):
        if cur.strip().lower() == 'brl':
            return DEFAULT_CURRENCY
        return None
    try:
        code = int(cur)
    except (TypeError, ValueError):
        return None
    return code if CURRENCY.get(code) else None


def currency_symbol(cur):
    """Símbolo da moeda (`'R$'`) a partir do código/legado; '' se desligado."""
    code = normalize_currency(cur)
    info = CURRENCY.get(code) if code is not None else None
    return info['symbol'] if info else ''


def fmt_money(value, cur=DEFAULT_CURRENCY):
    """Formata valor monetário pelo código de `CURRENCY` (filtro `money`).

    `fmt_money(v)` sem código = padrão (BRL), idêntico ao antigo `fmt_brl`.
    """
    code = normalize_currency(cur)
    if code is None:
        code = DEFAULT_CURRENCY
    info = CURRENCY.get(code) or CURRENCY[DEFAULT_CURRENCY]
    num = _fmt_number(value, info['locale'])
    return f"{info['symbol']} {num}" if info['symbol'] else num


def fmt_percent(value):
    """Formata percentual com 1 decimal e sufixo '%' (ex.: 12.5 → '12,5%')."""
    if value is None:
        return '—'
    return f'{value:,.1f}'.replace(',', 'X').replace('.', ',').replace('X', '.') + '%'


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


def _iter_path_leaves(obj, path):
    """Gera os valores nas folhas de `path` (ex.: 'items.quantidade'),
    percorrendo coleções encontradas pelo caminho."""
    if obj is None or not path:
        return
    parts = path.split('.')

    def walk(node, i):
        if node is None:
            return
        if i == len(parts):
            yield node
            return
        if isinstance(node, (list, tuple, set)):
            for child in node:
                yield from walk(child, i)
            return
        if isinstance(node, dict):
            val = node.get(parts[i])
        else:
            val = getattr(node, parts[i], None)
        yield from walk(val, i + 1)

    yield from walk(obj, 0)


def field_value(field, item):
    """Valor de um campo para `item`: resolve campos derivados
    (`{'sum': 'caminho'}` = soma das folhas) senão acesso aninhado."""
    derived = getattr(field, 'derived', None)
    if derived:
        path = derived.get('sum')
        if not path:
            return None
        total = None
        for v in _iter_path_leaves(item, path):
            if v is None:
                continue
            total = (v if total is None else total + v)
        return total
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


def fmt_zero(value):
    if not value:
        return ''
    return "%.1f" % value


def fmt_date(value):
    if not value:
        return ""
    return value.strftime("%d/%m/%Y")


def fmt_zero_int(value):
    if not value:
        return ''
    return "%.0f" % value


def fmt_datetime(value):
    if not value:
        return ''
    try:
        return value.strftime('%d/%m/%Y %H:%M')
    except AttributeError:
        return str(value)


def _title_case(text):
    words = text.strip().split()
    result = []
    for i, w in enumerate(words):
        if i > 0 and w.lower() in CONECTORES:
            result.append(w.lower())
        else:
            result.append(w[0].upper() + w[1:].lower() if w else w)
    return " ".join(result)


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


import re


def apply_transform(text, mode):
    """Efeito de texto: 'upper' | 'title' | 'lower' (None/other = intacto)."""
    if not text or not mode:
        return text
    mode = mode.lower()
    if mode == 'upper':
        return str(text).upper()
    if mode == 'lower':
        return str(text).lower()
    if mode == 'title':
        return str(text).title()
    return text
