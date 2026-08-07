"""Helpers genéricos de formatação/utilidade do framework.

Reutilizados por templates (filtros Jinja) e pelo motor de listagem/formulário.
Não dependem de modelos nem da aplicação host.
"""
from app.ajsystem.constants import CONECTORES


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


def item_ref(item, siblings):
    """Identificador curto do registro para cabeçalhos de coluna (tabela
    transposta): usa a(s) coluna(s) da chave primária que variam entre os
    itens irmãos. Ex.: ProductIngredient -> ingredient_id; OrderItem -> id.
    Retorna None quando não há como identificar (item novo/sem pk)."""
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
