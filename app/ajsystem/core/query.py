"""Motor de consultas nomeadas (`Query`) — agrupamento e totais sobre listas.

Uma `Query` é um dict (mesmo estilo de `Entity`, `List`, `Form`), sem função
de definição. O rótulo padrão vem do nome da chave:

    Query = {
        'pedidos': {
            'fields': ['Item'],               # entidades e/ou campos explícitos
            'group_by': 'status',
            'order_by': 'data desc',
            'totals': {
                'Qtd':    {'sum': 'qtd'},
                'Valor':  {'sum': 'total', 'currency': True},
                'Média':  {'avg': 'total', 'currency': True},
                'Média/Qtd': {'avg': 'total', 'by': 'qtd', 'currency': True},
            },
            # fonte SQL global (fase 2): join / where / raw ('with x as (...) select ...')
        },
    }

Agregações:
  'count'                          → número de itens
  {'sum': campo}                   → soma (resolve campos derivados)
  {'avg': campo}                   → média sobre itens com valor
  {'avg': campo, 'by': divisor}    → soma(campo) / soma(divisor)  (média ponderada)
  'currency': True                 → formata como BRL na renderização
"""
import functools

from app.ajsystem.core.utils import _title_case, field_value, query_label  # noqa: F401


def _option_label(field, key):
    """Rótulo de uma opção (suporta options com chave int/str vs valor)."""
    if field is None or not field.options:
        return key
    for ok, ol in field.options.items():
        if str(ok) == str(key):
            return ol
    return key


def _value_for(item, field_name, fields):
    """Valor do campo para `item`: resolve campos derivados e caminhos dotted."""
    if fields:
        for f in fields:
            if f.name == field_name:
                return field_value(f, item)
    return getattr(item, field_name, None)


def _cmp_value(a, b):
    """Comparação tolerante a None (None vem antes) e tipos mistos."""
    if a is None and b is None:
        return 0
    if a is None:
        return -1
    if b is None:
        return 1
    try:
        return (a > b) - (a < b)
    except TypeError:
        a, b = str(a), str(b)
        return (a > b) - (a < b)


def order_items(items, order_by, fields=None):
    """Ordena itens por spec (ex.: 'data_pedido desc' ou lista de colunas). Estável."""
    if not order_by or not items:
        return items
    if isinstance(order_by, str):
        parts = [p.strip() for p in order_by.split(',') if p.strip()]
    else:
        parts = list(order_by or [])
    specs = []
    for p in parts:
        words = p.split()
        specs.append((words[0], len(words) > 1 and words[1].lower() in ('desc', 'reverse')))

    def _cmp(a, b):
        for name, desc in specs:
            r = _cmp_value(_value_for(a, name, fields), _value_for(b, name, fields))
            if r:
                return -r if desc else r
        return 0

    return sorted(items, key=functools.cmp_to_key(_cmp))


def aggregate_rows(items, spec, fields=None):
    """Aplica um spec de totais ({label: 'count' | {'sum'|'avg': campo, ...}}).

    Retorna {label: {'type': ..., 'field': ..., 'currency': bool, 'value': ...}}.
    Divisor zero (avg com `by` zerado) → value None (renderiza '—').
    """
    totals = {}
    for label, agg in (spec or {}).items():
        if isinstance(agg, dict) and agg.get('sum'):
            field_name = agg['sum']
            s = None
            for it in items:
                v = _value_for(it, field_name, fields)
                if v is None:
                    continue
                s = (v if s is None else s + v)
            totals[label] = {
                'type': 'sum', 'field': field_name,
                'currency': bool(agg.get('currency')), 'value': s,
            }
        elif isinstance(agg, dict) and agg.get('avg'):
            field_name = agg['avg']
            s = None
            n = 0
            for it in items:
                v = _value_for(it, field_name, fields)
                if v is None:
                    continue
                s = (v if s is None else s + v)
                n += 1
            by = agg.get('by')
            if by:
                divisor = None
                for it in items:
                    d = _value_for(it, by, fields)
                    if d is None:
                        continue
                    divisor = (d if divisor is None else divisor + d)
            else:
                divisor = n
            value = None if not divisor or s is None else s / divisor
            totals[label] = {
                'type': 'avg', 'field': field_name,
                'currency': bool(agg.get('currency')), 'value': value,
            }
        else:
            totals[label] = {'type': 'count', 'value': len(items)}
    return totals


def group_items(items, field, spec, fields=None):
    """Agrupa itens pelo campo, na ordem das options (senão, por valor)."""
    present = {}
    for it in items:
        key = _value_for(it, field.name, fields) if field is not None else None
        present.setdefault(key, []).append(it)
    if field is not None and field.options:
        matched = []
        matched_keys = set()
        for ok in field.options.keys():
            for pk in present.keys():
                if str(ok) == str(pk):
                    matched.append(pk)
                    matched_keys.add(pk)
                    break
        rest = [k for k in present.keys() if k not in matched_keys]
        keys = matched + sorted(rest, key=lambda k: str(k))
    else:
        keys = sorted(present.keys(), key=lambda k: str(k))
    return [
        {
            'key': k,
            'label': _option_label(field, k),
            'items': present[k],
            'totals': aggregate_rows(present[k], spec, fields),
        }
        for k in keys
    ]
