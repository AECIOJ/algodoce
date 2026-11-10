"""Resolve um gráfico declarado em `ReportBody.chart` em `ChartDataset`.

Reusa o pipeline de dados do relatório (`_auto_data`): a mesma `source`
(entity/query/pivot), o mesmo `body.filter` e a mesma gramática de filtros.
A agregação é feita sobre as linhas resolvidas, agrupando pela categoria.
"""
import locale
from datetime import date, datetime

from ajsystem.defs.chart import (Chart, ChartField, ChartDataset,
                                 normalize_chart, parse_chart)

# Alias de máscara de data/hora para strftime.
_LABEL_FORMATS = {
    'mmm/yyyy': '%b/%Y',
    'mmm/yy': '%b/%y',
    'mm/yyyy': '%m/%Y',
    'mm/yy': '%m/%y',
    'dd/mm/yyyy': '%d/%m/%Y',
    'dd/mm/yy': '%d/%m/%y',
    'yyyy-mm': '%Y-%m',
    'yyyy-mm-dd': '%Y-%m-%d',
    'yyyy': '%Y',
}

# Nomes curtos de mês em português (fallback quando o locale pt-BR
# não está instalado no sistema, ex.: imagem python:*-slim).
_MES_PT = {
    '01': 'Jan', '02': 'Fev', '03': 'Mar', '04': 'Abr',
    '05': 'Mai', '06': 'Jun', '07': 'Jul', '08': 'Ago',
    '09': 'Set', '10': 'Out', '11': 'Nov', '12': 'Dez',
}


def _set_pt_locale():
    """Tenta definir locale pt-BR para %b renderizar 'Mai', 'Jun', etc."""
    for cand in ('pt_BR.UTF-8', 'pt_BR.utf8', 'pt_BR', 'ptb', 'Portuguese_Brazil.1252'):
        try:
            locale.setlocale(locale.LC_TIME, cand)
            return True
        except locale.Error:
            continue
    return False


_set_pt_locale()


def _fmt_label(value, fmt):
    """Formata uma label de categoria já agrupada por `bin`.

    `value` vem como string crua do bin ('YYYY-MM' / 'YYYY' / 'YYYY-MM-DD').
    `fmt` pode ser um strftime direto ou um alias de `_LABEL_FORMATS`.
    """
    if not value or not fmt:
        return value
    # Resolve alias.
    pyfmt = _LABEL_FORMATS.get(fmt, fmt)
    try:
        if isinstance(value, str):
            # Chaves de bin: 'YYYY-MM' / 'YYYY' / 'YYYY-MM-DD'.
            for cand in ('%Y-%m-%d', '%Y-%m', '%Y'):
                try:
                    dt = datetime.strptime(value, cand)
                    resultado = dt.strftime(pyfmt)
                    # %b depende do locale pt-BR, que pode não estar
                    # instalado (imagem python:*-slim). Usa mapeamento manual.
                    if '%b' in pyfmt:
                        mes_pt = _MES_PT.get(dt.strftime('%m'), dt.strftime('%m'))
                        resultado = resultado.replace(dt.strftime('%b'), mes_pt)
                    return resultado
                except ValueError:
                    continue
        return value
    except (ValueError, TypeError):
        return value


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


def _bin(value, bin_):
    """Agrupa datas por dia/mês/ano; devolve o valor original fora de data."""
    if bin_ is None or value is None:
        return value
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    if isinstance(value, (datetime, date)):
        if bin_ == 'day':
            return value.strftime('%Y-%m-%d')
        if bin_ == 'month':
            return value.strftime('%Y-%m')
        if bin_ == 'year':
            return value.strftime('%Y')
    return value


def _field_labels(report, names):
    """Rótulo de exibição de cada campo (Entity do report; fallback auto)."""
    from ajsystem.defs.data import _auto_label
    labels = {name: _auto_label(name) for name in names}
    try:
        from ajsystem.core.do_report import (_body_of, _entity_cfg_for,
                                             _module_entity,
                                             _source_entity_name)
        body = _body_of(report)
        src = _get(body, 'source')
        cfg = _entity_cfg_for(_module_entity(report),
                              _source_entity_name(src))
    except Exception:
        return labels
    for name in names:
        item = cfg.get(name) or {}
        if isinstance(item, dict) and item.get('label'):
            labels[name] = item['label']
    return labels


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

    `chart.order`, quando declarado, injeta `ORDER BY` na query de origem
    antes da execução (igual `ReportBody.order`).
    """
    from ajsystem.core.do_report import _auto_data, _body_of
    if chart is None:
        chart = load_chart(report, variant=variant, syn=syn)

    rows = _auto_data(report, None, None, filter, syn=False,
                      chart_order=chart.order) or []
    return _build_dataset(report, chart, rows)


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


def _explode_flags(chart, cat_name, labels):
    """Flags por ponto de `options.explode` (pie/donut).

    Sem `cat`, casa com as chaves de `value`; com `cat`, com o valor da
    categoria. Nome inexistente é ignorado em silêncio.
    """
    spec = getattr(chart.options, 'explode', None)
    if not spec:
        return None
    wanted = {spec} if isinstance(spec, str) else set(spec)
    if cat_name is None:
        return [name in wanted for name in chart.value]
    return [str(label) in wanted for label in labels]


def _build_dataset(report, chart, rows):
    from ajsystem.core.pdf import _agg_apply

    cat_name = next(iter(chart.cat), None)
    field_labels = _field_labels(report, list(chart.value))

    if cat_name is None:
        # Sem `cat`: os rótulos são os campos declarados em `value` e cada um
        # entra como uma categoria, com o próprio valor agregado. É o formato
        # de "comparar totais" (ex.: pizza com uma fatia por campo de `value`).
        labels = [field_labels[name] for name in chart.value]
        display_labels = labels
        series = [{
            'name': chart.label.value or chart.title or '',
            'data': [
                _agg_apply(cfg.agg, [_row_get(r, name) for r in rows])
                for name, cfg in chart.value.items()
            ],
            'type': None,
            'axis': 'y',
            'color': None,
            'colors': [cfg.color for cfg in chart.value.values()],
            'stack': None,
            'format': None,
        }]
        limit = None
    else:
        cat_cfg = chart.cat.get(cat_name) or ChartField()
        groups = {}
        order = []
        for row in rows:
            key = _bin(_row_get(row, cat_name), cat_cfg.bin)
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(row)

        labels = list(order)
        # Com bin (agrupamento de data), as chaves são strings 'YYYY-MM' /
        # 'YYYY', que ordenam corretamente como texto. Ordena cronologicamente
        # por padrão, a menos que order seja 'asc'/'desc' (ordena por valor).
        if cat_cfg.bin and cat_cfg.order not in ('asc', 'desc'):
            labels = sorted(labels)
        # `labels` segue sendo a chave crua (usada para buscar em `groups`).
        # `display_labels` recebe a versão formatada (ex.: 'mmm/yyyy' -> 'Mai/2026')
        # quando há `format` em `cat` com `bin`.
        if cat_cfg.bin and cat_cfg.format:
            display_labels = [_fmt_label(k, cat_cfg.format) for k in labels]
        else:
            display_labels = labels
        series = []
        for field_name, cfg in chart.value.items():
            data = [
                _agg_apply(cfg.agg,
                           [_row_get(r, field_name) for r in groups[k]])
                for k in labels
            ]
            series.append({
                'name': field_labels[field_name],
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
            idx = sorted(range(len(labels)),
                         key=lambda i: _sort_key(base[i]),
                         reverse=(cat_cfg.order == 'desc'))
            labels = [labels[i] for i in idx]
            display_labels = [display_labels[i] for i in idx]
            for s in series:
                s['data'] = [s['data'][i] for i in idx]

        limit = cat_cfg.limit or chart.limit
        if limit:
            labels = labels[:limit]
            display_labels = display_labels[:limit]
            for s in series:
                s['data'] = s['data'][:limit]

    # Destaca fatias só no desenho: flags já reordenadas/cortadas.
    flags = _explode_flags(chart, cat_name, display_labels)
    if flags and series:
        series[0]['explode'] = flags

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
    return ChartDataset(labels=display_labels, series=series, meta=meta)
