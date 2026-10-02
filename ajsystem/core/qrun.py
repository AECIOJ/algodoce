"""QRun — executor genérico de QuerySpec/OverSpec (SQL filtra, janela numera).

Genérico: não cita entidade do app. Recebe model + QuerySpec + entity_cfg
({campo: cfg} p/ cast) e devolve linhas (instâncias + attrs computados).

Fase 1: WHERE/ORDER/LIMIT/GROUP BY no SQL; OVER avaliado em passo único
em Python sobre o resultado (1 query, sem N+1). O spec já é o final
(func/agg/over/display); o pushdown p/ OVER SQL puro (OVER no banco +
CTE recursiva) entra na fase 2 sem mudar o spec.
"""
from collections import defaultdict

from ajsystem.defs.qspec import parse_query


def _cast_value(cfg, value):
    if value is None or isinstance(value, (int, float, bool)):
        return value
    t = (cfg or {}).get('type')
    if t in ('INT', 'ID', 'FK', 'LIST'):
        try:
            return int(value)
        except (TypeError, ValueError):
            return value
    if t == 'BOOL':
        if isinstance(value, str):
            return value.strip().lower() not in ('', '0', 'false', 'não', 'nao')
        return bool(value)
    return value


def apply_where(query, model, where, entity_cfg):
    if not where:
        return query
    if isinstance(where, dict):
        where = [where]
    for cond in where:
        for campo, valor in (cond or {}).items():
            if valor is None or valor == '':
                continue
            col = getattr(model, campo, None)
            if col is None:
                continue
            cfg = (entity_cfg or {}).get(campo, {})
            if isinstance(valor, (list, tuple, set)):
                vals = [_cast_value(cfg, v) for v in valor]
                query = query.filter(col.in_(vals))
            else:
                query = query.filter(col == _cast_value(cfg, valor))
    return query


def _order_cols(model, order):
    cols = []
    if not order:
        return cols
    if isinstance(order, str):
        order = [order]
    for item in order:
        if isinstance(item, dict):
            fname = item.get('field')
            desc = (item.get('direction') or 'asc').lower() == 'desc'
        elif isinstance(item, str):
            parts = item.split()
            fname, desc = parts[0], len(parts) > 1 and parts[1].lower() == 'desc'
        else:
            continue
        col = getattr(model, fname, None)
        if col is not None:
            cols.append(col.desc().nullslast() if desc else col.asc().nullsfirst())
    return cols


def _entries_over(entries):
    return [e for e in entries if e.over is not None]


def _compute_calc(rows, entries):
    """Avalia calc (template) pós-over, em ordem do select. Fonte única p/
    montados (ex. indice) — grade e relatório bebem o mesmo attr."""
    import re as _re
    from ajsystem.core.text import render as _render
    for e in entries or []:
        if not e.calc:
            continue
        for r in rows:
            setattr(r, e.name, _render(e.calc, lambda k, _r=r: getattr(_r, k, None)))
    return rows


def _validate_calc(entries, model):
    import re as _re
    cols = set(getattr(model, '__table__', None).columns.keys()) if getattr(model, '__table__', None) is not None else set()
    known = cols | {e.name for e in entries or []}
    for e in entries or []:
        if not e.calc:
            continue
        for nm in set(_re.findall(r'{\??(\w+)', e.calc)):
            if nm not in known:
                raise ValueError(f"select '{e.name}': calc referencia campo desconhecido '{nm}'")


def _eval_key(row, key):
    """Avalia 1 chave normalizada ('field'| 'expr') sobre a linha."""
    kind = key[0]
    if kind == 'field':
        return getattr(row, key[1], None)
    if kind == 'expr' and key[1] == 'coalesce':
        for f in key[2]:
            v = getattr(row, f, None)
            if v is not None:
                return v
        return None
    raise ValueError(f"expressão '{key[1]}' sem avaliador em qrun")


def _skey_for(okeys):
    # Convenção do motor (igual a core/query._cmp_value): None vem antes no
    # asc (raiz com pai_id null abre o grupo), por último no desc.
    def _skey(r):
        out = []
        for key in okeys:
            desc = key[-1]
            v = _eval_key(r, key)
            out.append((v is not None, v) if not desc else (v is None, v))
        return out
    return _skey


def _compute_over(rows, entries, model=None):
    """Avalia overs em passo único (partição/ordem em Python, 1 query já feita)."""
    from ajsystem.defs.qspec import normalize_order
    if model is not None:
        _validate_expr_fields(model, entries)
    for e in _entries_over(entries):
        ov = e.over
        part_keys = ov.partition or []
        okeys = getattr(ov, 'okeys', None) or normalize_order(ov.order or [])

        def _pkey(r):
            return tuple(getattr(r, k, None) for k in part_keys)

        _skey = _skey_for(okeys)

        groups = defaultdict(list)
        for r in rows:
            groups[_pkey(r)].append(r)
        for _, members in groups.items():
            members.sort(key=_skey)
            n = len(members)
            func = (ov.func or '').lower()

            def _rkey(r):
                return tuple(_eval_key(r, k) for k in okeys)
            if func == 'rownumber':
                for i, r in enumerate(members, 1):
                    setattr(r, e.name, i)
            elif func == 'rank':
                rank, prev, seen = 1, None, 0
                for r in members:
                    key = _rkey(r)
                    seen += 1
                    if prev is not None and key != prev:
                        rank = seen
                    setattr(r, e.name, rank)
                    prev = key
            elif func == 'denserank':
                rank, prev = 0, None
                for r in members:
                    key = _rkey(r)
                    if prev is None or key != prev:
                        rank += 1
                    setattr(r, e.name, rank)
                    prev = key
            elif func in ('lag', 'lead'):
                src = ov.field or e.field
                off = max(1, int(ov.offset or 1))
                for i, r in enumerate(members):
                    j = i - off if func == 'lag' else i + off
                    setattr(r, e.name, getattr(members[j], src, None) if 0 <= j < n else ov.default)
            elif func in ('firstvalue', 'lastvalue'):
                src = ov.field or e.field
                v = getattr(members[0] if func == 'firstvalue' else members[-1], src, None) if members else None
                for r in members:
                    setattr(r, e.name, v)
            elif func == 'nthvalue':
                src = ov.field or e.field
                idx = max(1, int(ov.count or 1)) - 1
                v = getattr(members[idx], src, None) if idx < n else ov.default
                for r in members:
                    setattr(r, e.name, v)
            elif func == 'ntile':
                b = max(1, int(ov.count or 4))
                for i, r in enumerate(members):
                    setattr(r, e.name, min(b, i * b // max(1, n) + 1))
            elif func in ('sum', 'avg', 'min', 'max', 'count'):
                src = ov.field or e.field
                vals = [getattr(r, src, None) for r in members]
                nums = [v for v in vals if v is not None]
                if func == 'sum':
                    v = sum(nums) if nums else None
                elif func == 'avg':
                    v = (sum(nums) / len(nums)) if nums else None
                elif func == 'min':
                    v = min(nums) if nums else None
                elif func == 'max':
                    v = max(nums) if nums else None
                else:
                    v = len(nums)
                for r in members:
                    setattr(r, e.name, v)
            elif ov.agg in ('sum', 'avg', 'min', 'max', 'count'):
                src = ov.field or e.field
                vals = [getattr(r, src, None) for r in members]
                nums = [v for v in vals if v is not None]
                if ov.agg == 'sum':
                    v = sum(nums) if nums else None
                elif ov.agg == 'avg':
                    v = (sum(nums) / len(nums)) if nums else None
                elif ov.agg == 'min':
                    v = min(nums) if nums else None
                elif ov.agg == 'max':
                    v = max(nums) if nums else None
                else:
                    v = len(nums)
                for r in members:
                    setattr(r, e.name, v)
    return rows


def _validate_expr_fields(model, entries):
    """fail-fast: campos de expressão têm que existir no model."""
    cols = set(getattr(model, '__table__', None).columns.keys()) if getattr(model, '__table__', None) is not None else set()
    for e in _entries_over(entries or []):
        for key in (getattr(e.over, 'okeys', None) or []):
            if key[0] == 'expr':
                for f in key[2]:
                    if f not in cols:
                        raise ValueError(f"over '{e.name}': campo '{f}' não existe em {getattr(model, '__name__', model)}")


def _sort_rows(rows, order, model):
    """Ordenação final incluindo computados (grupo/index) — estável sobre o SQL."""
    from ajsystem.defs.qspec import normalize_order
    okeys = normalize_order(order)
    if not okeys:
        return rows
    cols = set(getattr(model, '__table__', None).columns.keys()) if getattr(model, '__table__', None) is not None else set()
    for key in okeys:
        fields = [key[1]] if key[0] == 'field' else list(key[2])
        for f in fields:
            if f not in cols and not hasattr(rows[0] if rows else object(), f):
                raise ValueError(f"query.order: campo '{f}' não existe (nem coluna, nem computado)")
    return sorted(rows, key=_skey_for(okeys))


def build_levels(rows, pk='id', parent='pai_id', rn_attr='rn',
                   group='tipo', root_fmt='{g:02d}.{rn:02d}',
                   child_fmt='{parent}.{rn:02d}', target='indice',
                   max_depth=20):
    """Numeração hierárquica genérica em passo único (1 query já feita).

    rn_attr vem do over rownumber por (group, parent). Monta path + sort_path
    (tupla de ints p/ ordenação numérica) e o rótulo target. Sem SQL recursivo
    nesta fase; mesma assinatura servirá ao pushdown CTE depois.
    """
    by_id = {getattr(r, pk, None): r for r in rows}
    children = {}
    for r in rows:
        children.setdefault(getattr(r, parent, None), []).append(r)
    for members in children.values():
        members.sort(key=lambda r: (getattr(r, rn_attr, 0) or 0))

    def _walk(node, path, depth):
        rn = getattr(node, rn_attr, 0) or 0
        if depth == 0:
            g = getattr(node, group, 0) or 0
            try:
                label = root_fmt.format(g=int(g), rn=int(rn))
            except (ValueError, TypeError):
                label = root_fmt.format(g=g, rn=rn)
            sp = (int(g) if str(g).isdigit() else 0, int(rn))
        else:
            ppath, plabel = path
            try:
                label = child_fmt.format(parent=plabel, rn=int(rn))
            except (ValueError, TypeError):
                label = child_fmt.format(parent=plabel, rn=rn)
            sp = ppath + (int(rn),)
        setattr(node, target, label)
        setattr(node, 'sortpath', sp)
        if depth >= max_depth:
            return
        for ch in children.get(getattr(node, pk, None), []):
            if getattr(ch, pk, None) == getattr(node, pk, None):
                continue
            _walk(ch, (sp, label), depth + 1)

    roots = sorted(children.get(None, []),
                   key=lambda r: ((getattr(r, group, 0) or 0),
                                  (getattr(r, rn_attr, 0) or 0)))
    for rt in roots:
        _walk(rt, ((), ''), 0)
    # órfãos (pai ausente): trata como raiz do próprio grupo
    for r in rows:
        if not hasattr(r, target):
            p = getattr(r, parent, None)
            if p is not None and p not in by_id:
                g = getattr(r, group, 0) or 0
                rn = getattr(r, rn_attr, 0) or 0
                setattr(r, target, root_fmt.format(g=int(g), rn=int(rn)))
                setattr(r, 'sortpath', (int(g), int(rn)))
    rows.sort(key=lambda r: getattr(r, 'sortpath', ()))
    return rows


build_hierarchy = build_levels  # alias legado


def run_query(model, spec, entity_cfg=None, extra_where=None):
    """Executa QuerySpec sobre model. Devolve list de instâncias (+ attrs over)."""
    qs = parse_query(spec)
    from sqlalchemy import func as _fn
    query = model.query
    query = apply_where(query, model, qs.where, entity_cfg)
    query = apply_where(query, model, extra_where, entity_cfg)

    # GROUP BY + aggs fora de over -> agregação SQL (reduz linhas)
    group_fields = list(qs.groups or [])
    agg_entries = [e for e in (qs.entries or []) if e.agg and e.over is None]
    if group_fields or agg_entries:
        cols, labels = [], []
        for g in group_fields:
            col = getattr(model, g, None)
            if col is not None:
                cols.append(col)
        for e in agg_entries:
            col = getattr(model, e.field or e.name, None)
            fn = (e.agg or '').lower()
            if col is None:
                continue
            agg = {'count': _fn.count, 'sum': _fn.sum, 'avg': _fn.avg,
                   'min': _fn.min, 'max': _fn.max}[fn](col).label(e.name)
            cols.append(agg)
            labels.append(e.name)
        if cols:
            q = model.query.with_entities(*cols)
            q = apply_where(q, model, qs.where, entity_cfg)
            q = apply_where(q, model, extra_where, entity_cfg)
            if group_fields:
                q = q.group_by(*[getattr(model, g) for g in group_fields
                                 if getattr(model, g, None) is not None])
            ocols = _order_cols(model, qs.order)
            if ocols:
                q = q.order_by(*ocols)
            if qs.limit:
                q = q.limit(int(qs.limit))

            class _Row:
                pass
            rows = []
            gnames = [g for g in group_fields if getattr(model, g, None) is not None]
            for tup in q.all():
                vals = list(tup) if isinstance(tup, (tuple, list)) else [tup]
                r = _Row()
                for k, v in zip(gnames + labels, vals):
                    setattr(r, k, v)
                setattr(r, 'id', getattr(r, 'id', None))
                rows.append(r)
            return rows

    ocols = _order_cols(model, qs.order)
    if ocols:
        query = query.order_by(*ocols)
    if qs.limit:
        query = query.limit(int(qs.limit))
    rows = list(query.all())
    _validate_calc(qs.entries or [], model)
    rows = _compute_over(rows, qs.entries or [], model)
    rows = _compute_calc(rows, qs.entries or [])
    rows = _sort_rows(rows, qs.order, model)
    hier = (spec.get('levels', spec.get('hierarchy')) if isinstance(spec, dict) else None)
    if hier:
        if not isinstance(hier, dict):
            raise TypeError("query.levels deve ser dict")
        rows = build_levels(rows, pk=hier.get('pk', 'id'),
                               parent=hier.get('parent', 'pai_id'),
                               rn_attr=hier.get('using', 'rn'),
                               group=hier.get('group', 'tipo'),
                               root_fmt=hier.get('root', '{g:02d}.{rn:02d}'),
                               child_fmt=hier.get('child', '{parent}.{rn:02d}'),
                               target=hier.get('target', 'indice'),
                               max_depth=int(hier.get('maxdepth', 20)))
    return rows
