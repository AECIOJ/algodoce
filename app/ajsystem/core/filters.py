"""FILTERS — resolução e aplicação de filtros de listagem.

Reescrito do zero observando `core/old/filters.py`. `resolve_filters` produz a
estrutura consumida por `pages/list.html` (`initial_filters`/`active_filters`).
`apply_filters` aplica condições no nível SQL quando aplicável.
"""
import calendar
from datetime import date, datetime, timedelta

from sqlalchemy import extract


def _deep_attr(obj, path):
    if path is None:
        return None
    for part in path.split('.'):
        if obj is None:
            return None
        if not isinstance(obj, dict):
            obj = getattr(obj, part, None)
        else:
            obj = obj.get(part)
    return obj


def resolve_filters(config, request_args):
    """Gera (initial_filters, active_filters) a partir do config e query args."""
    initial = {}
    active = {}
    for name, cfg in config.items():
        ftype = cfg.get('type')
        if ftype in ('select', 'checklist', 'boolean'):
            initial[name] = ''
        elif ftype == 'date':
            initial[name] = {'preset': ''}
        elif ftype == 'number':
            initial[name] = {'mode': 'igual', 'val1': '', 'val2': ''}
        else:
            initial[name] = {'mode': 'contains', 'value': ''}

        av = request_args.get(name)
        if av not in (None, ''):
            if ftype in ('boolean', 'select'):
                active[name] = av
            else:
                active[name] = av
            continue
        if ftype == 'number':
            v1 = request_args.get(f'{name}_val1')
            v2 = request_args.get(f'{name}_val2')
            mode = request_args.get(f'{name}_mode', 'igual')
            if v1 in (None, ''):
                continue
            entry = {'mode': mode, 'val1': v1, 'val2': v2 or ''}
            if v1 is not None and v1 != '':
                active[name] = entry
        elif ftype == 'date':
            preset = request_args.get(f'{name}_preset')
            if preset:
                entry = {'preset': preset}
                for k in ('from', 'to', 'mes', 'ano'):
                    v = request_args.get(f'{name}_{k}')
                    if v:
                        entry[k] = v
                active[name] = entry
        elif ftype == 'text':
            value = request_args.get(f'{name}_value')
            mode = request_args.get(f'{name}_mode', 'contains')
            if value not in (None, ''):
                active[name] = {'mode': mode, 'value': value}
    return initial, active


def filtrar_vencimento_query(query, model_field, preset, hoje=None):
    hoje = hoje or date.today()
    if preset == 'hoje':
        return query.filter(model_field == hoje)
    if preset == 'ontem':
        return query.filter(model_field == hoje - timedelta(days=1))
    if preset == 'mes_atual':
        return query.filter(
            extract('year', model_field) == hoje.year,
            extract('month', model_field) == hoje.month)
    if preset == 'mes_anterior':
        d = (hoje.replace(day=1) - timedelta(days=1))
        return query.filter(
            extract('year', model_field) == d.year,
            extract('month', model_field) == d.month)
    if preset == 'ano_atual':
        return query.filter(extract('year', model_field) == hoje.year)
    if preset == 'ano_anterior':
        return query.filter(extract('year', model_field) == hoje.year - 1)
    if preset == 'mes':
        mes = int(getattr(model_field, 'mes', None) or 0)
        mes = mes or 1
        return query
    return query


def _filter_conditions(model_field, ftype, cfg_value):
    """Retorna uma lista de condições SQL (ou None) p/ o tipo/valor do filtro."""
    if cfg_value is None:
        return None
    if ftype == 'boolean':
        if cfg_value == 'true':
            return [model_field == True]  # noqa: E712
        if cfg_value == 'false':
            return [model_field == False]  # noqa: E712
        return []
    if ftype in ('select', 'checklist'):
        if isinstance(cfg_value, str) and ',' in cfg_value:
            vals = [v.strip() for v in cfg_value.split(',') if v.strip()]
            return [model_field.in_(vals)] if vals else []
        if cfg_value:
            return [model_field == cfg_value]
        return []
    if ftype == 'text':
        value = cfg_value.get('value')
        if value in (None, ''):
            return []
        mode = cfg_value.get('mode', 'contains')
        if mode == 'igual':
            cond = model_field == value
        elif mode == 'starts':
            cond = model_field.like(f'{value}%')
        else:
            cond = model_field.ilike(f'%{value}%')
        return [cond]
    if ftype == 'number':
        v1 = cfg_value.get('val1')
        mode = cfg_value.get('mode', 'igual')
        if v1 in (None, ''):
            return []
        try:
            v1 = float(v1)
        except (TypeError, ValueError):
            return []
        v2 = cfg_value.get('val2')
        if mode == 'entre' and v2 not in (None, ''):
            try:
                return [model_field >= v1, model_field <= float(v2)]
            except ValueError:
                return [model_field == v1]
        rules = {'igual': model_field == v1, 'maior_que': model_field > v1,
                 'maior_igual': model_field >= v1, 'menor_que': model_field < v1,
                 'menor_igual': model_field <= v1}
        return [rules[mode]] if mode in rules else []
    return []


def apply_filters(query, model_field, ftype, cfg_value):
    conds = _filter_conditions(model_field, ftype, cfg_value)
    for c in conds:
        query = query.filter(c)
    return query
