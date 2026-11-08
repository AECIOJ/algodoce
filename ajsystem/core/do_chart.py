"""Resolve um gráfico declarado em `ReportBody.chart` em `ChartDataset`.

Reusa o pipeline de dados do relatório (`_auto_data`): a mesma `source`
(entity/query/pivot), o mesmo `body.filter` e a mesma gramática de filtros.
A agregação é feita sobre as linhas resolvidas, agrupando pela categoria.
"""
from datetime import date, datetime

from ajsystem.defs.chart import (Chart, ChartField, ChartDataset,
                                 normalize_chart, parse_chart)


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default) if obj is not None else default


def _row_get(row, field):
    if isinstance(row, dict):
        return row.get(field)
    mapping = getattr(row, '_mapping', None)
    if mapping is not None:
        try:
            return mapping[field]
        except (KeyError, TypeError):
            pass
    return getattr(row, field, None)


def _row_keys(row):
    if isinstance(row, dict):
        return list(row.keys())
    table = getattr(row, '__table__', None)
    if table is not None:
        return [c.name for c in table.columns]
    mapping = getattr(row, '_mapping', None)
    if mapping is not None:
        return list(mapping.keys())
    return [k for k in dir(row) if not k.startswith('_')]


def _bucket(value, bucket):
    """Agrupa datas por dia/mês/ano; devolve o valor original fora de data."""
    if bucket is None or value is None:
        return value
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    if isinstance(value, (datetime, date)):
        if bucket == 'day':
            return value.strftime('%Y-%m-%d')
        if bucket == 'month':
            return value.strftime('%Y-%m')
        if bucket == 'year':
            return value.strftime('%Y')
    return value


def _sort_key(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _stack_of(chart, field):
    for group, fields in (chart.stack or {}).items():
        if field in fields:
            return group
    return None


def _subtitle(report):
    titles = _get(report, 'titles', None) or []
    if len(titles) < 2:
        return None
    sub = titles[1]
    if isinstance(sub, dict):
        return sub.get('text')
    return sub


def load_chart(report, *, variant=None, syn=False):
    """Resolve `ReportBody.chart` para o `Chart` ativo."""
    from ajsystem.core.do_report import _body_of
    body = _body_of(report)
    raw = _get(body, 'chart')
    if not raw:
        raise ValueError("report sem 'body.chart'")
    label = _get(report, 'label', '') or ''
    active = normalize_chart(raw, variant=variant, syn=syn, label=label)
    return parse_chart(active)


def resolve_chart(report, *, filter=None, variant=None, syn=False,
                  chart=None):
    """Resolve a declaração do gráfico em `ChartDataset` neutro.

    `report` é o `Report`/dict já resolvido (mesma fonte usada pelo PDF).
    `filter` é o spec literal vindo da request; é combinado com
    `body.filter` pelo próprio `_auto_data`.
    """
    from ajsystem.core.do_report import _auto_data
    if chart is None:
        chart = load_chart(report, variant=variant, syn=syn)
    rows = _auto_data(report, None, None, filter, syn=False) or []
    return _build_dataset(report, chart, rows)


def _build_dataset(report, chart, rows):
    from ajsystem.core.pdf import _agg_apply

    cat_name = next(iter(chart.cat), None)
    cat_cfg = chart.cat.get(cat_name) if cat_name else ChartField()

    if cat_name is None and rows:
        # Sem `cat` declarado: primeira coluna que não é série.
        for key in _row_keys(rows[0]):
            if key not in chart.value:
                cat_name = key
                cat_cfg = ChartField()
                break
    if cat_name is None:
        raise ValueError(
            "chart: 'cat' não declarado e não foi possível inferir da fonte")

    groups = {}
    order = []
    for row in rows:
        key = _bucket(_row_get(row, cat_name), cat_cfg.bucket)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(row)

    labels = list(order)
    series = []
    for field_name, cfg in chart.value.items():
        data = [
            _agg_apply(cfg.agg, [_row_get(r, field_name) for r in groups[k]])
            for k in labels
        ]
        series.append({
            'name': field_name,
            'data': data,
            'type': None,
            'axis': cfg.axis,
            'color': cfg.color,
            'stack': _stack_of(chart, field_name),
            'format': cfg.format,
        })

    # Ordenação pela primeira série (top N costuma olhar o valor).
    if cat_cfg.order in ('asc', 'desc') and series:
        base = series[0]['data']
        idx = sorted(range(len(labels)), key=lambda i: _sort_key(base[i]),
                     reverse=(cat_cfg.order == 'desc'))
        labels = [labels[i] for i in idx]
        for s in series:
            s['data'] = [s['data'][i] for i in idx]

    limit = cat_cfg.limit or chart.limit
    if limit:
        labels = labels[:limit]
        for s in series:
            s['data'] = s['data'][:limit]

    meta = {
        'title': chart.title or (_get(report, 'label', '') or ''),
        'subtitle': _subtitle(report),
        'filters': [],
        'total': len(rows),
        'empty': not labels,
        'warnings': [],
        'label': {
            'cat': chart.label.cat,
            'value': chart.label.value,
            'val': chart.label.val,
            'perc': chart.label.perc,
            'pos': chart.label.pos,
        },
        'limit': {
            'value': limit,
            'label': chart.label.limit,
        },
    }
    # Texto explicativo do limite quando aplicável
    if limit and chart.label.limit is not None:
        if chart.label.limit is True:
            meta['limit']['text'] = f"Top {limit}"
        elif isinstance(chart.label.limit, str):
            meta['limit']['text'] = chart.label.limit
        else:
            meta['limit']['text'] = f"Top {limit}"
    return ChartDataset(labels=labels, series=series, meta=meta)
