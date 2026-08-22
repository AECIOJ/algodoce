"""Helpers genéricos de formatação/utilidade do framework.

Reutilizados por templates (filtros Jinja) e pelo motor de listagem/formulário.
Não dependem de modelos nem da aplicação host.
"""
import re

from app.ajsystem.defs.constants import CONECTORES


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
    if value is None:
        return '0,00'
    return f'{value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


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
