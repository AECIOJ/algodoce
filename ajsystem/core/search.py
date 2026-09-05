"""SEARCH — buscas declaradas por página para modais de lookup.

Declaração na rota (ex. `recebimentos.py`):

    PREVISOES = {
        'source': 'Previsao',        # entidade-raiz (uma linha por registro)
        'join': 'transacao',         # relationship(s) p/ filtros/exibição
        'columns': ['id', 'documento', 'vencimento', 'previsto',
                    'realizado', 'variacao', 'saldo'],
        'when': ["transacao.tipo = 'R'", 'saldo > 0'],   # fixos
        'params': {'conta_id': 'transacao.conta_id'},     # arg request → igualdade
        'order': ['vencimento'],
    }

E o campo usa `lookup: {'display': 'id', 'query': 'PREVISOES'}`.

Execução: SQL para o seletivo (join + igualdades/IN em coluna) e Python para o
computado (`calc` da Entity/property, ex. `saldo`) e formatação. Sem os params
exigidos, retorna `{'need': [...]}` para o cliente pedir ao usuário.
"""
import re

_OPS = ('NOT IN', 'IN', '>=', '<=', '!=', '=', '>', '<', 'IS NOT NULL', 'IS NULL')
_COND_RE = re.compile(
    r'^\s*([A-Za-z_][A-Za-z0-9_.]*)\s*(NOT IN|IN|>=|<=|!=|=|>|<|IS NOT NULL|IS NULL)\s*(.*?)\s*$',
    re.IGNORECASE,
)


def _parse_cond(raw):
    """'a.b OP valor' → (path, OP, valor). Valor cru; coerção no uso."""
    m = _COND_RE.match(raw or '')
    if not m:
        return None
    return m.group(1), m.group(2).upper(), m.group(3)


def _model_entity(model):
    """Entity flat do model (`app.models.<snake>.Entity`) ou {}."""
    try:
        key = re.sub(r'(?<!^)(?=[A-Z])', '_', model.__name__).lower()
        mod = __import__(f'app.models.{key}', fromlist=['Entity'])
        ent = getattr(mod, 'Entity', None)
        return ent if isinstance(ent, dict) else {}
    except Exception:
        return {}


def _split_dotted(model, path):
    """Caminha relationship a partir do model; retorna (owner_model, attr)."""
    parts = (path or '').split('.')
    cur = model
    for p in parts[:-1]:
        rel = getattr(cur, p, None)
        try:
            cur = rel.property.mapper.class_
        except Exception:
            return None, parts[-1]
    return cur, parts[-1]


def _column_of(model, path):
    owner, attr = _split_dotted(model, path)
    if owner is None:
        return None
    try:
        return owner.__table__.columns.get(attr)
    except Exception:
        return None


def _coerce_scalar(v):
    from ajsystem.defs.data import _when_value
    return _when_value(v)


def _coerce_list(s):
    from ajsystem.defs.data import _when_in_list
    return _when_in_list(s)


def _sql_cond(query_col, op, raw, model):
    """Condição SQL para coluna real; None se o nome for computado."""
    from sqlalchemy import or_ as _or  # noqa
    if op in ('IS NULL', 'IS NOT NULL'):
        return query_col.is_(None) if op == 'IS NULL' else query_col.isnot(None)
    if op in ('IN', 'NOT IN'):
        vals = _coerce_list(raw)
        if not vals:
            return None
        return query_col.in_(vals) if op == 'IN' else ~query_col.in_(vals)
    v = _coerce_scalar(raw)
    if op == '=':
        return query_col == v
    if op == '!=':
        return query_col != v
    if op == '>':
        return query_col > v
    if op == '<':
        return query_col < v
    if op == '>=':
        return query_col >= v
    if op == '<=':
        return query_col <= v
    return None


def _py_val(row, path, entity):
    """Valor Python de uma coluna (dotted, property ou `calc` da Entity)."""
    from ajsystem.core.utils import calc_value, deep_attr
    if '.' in path:
        return deep_attr(row, path)
    cfg = (entity or {}).get(path, {}) or {}
    calc = cfg.get('calc')
    if calc is not None:
        try:
            return calc(row) if callable(calc) else calc_value(calc, row)
        except Exception:
            return None
    return deep_attr(row, path)


def _py_match(value, op, raw):
    """Compara valor Python (pós-fetch) — cobre computados em qualquer op."""
    if op == 'IS NULL':
        return value is None
    if op == 'IS NOT NULL':
        return value is not None
    if op in ('IN', 'NOT IN'):
        vals = _coerce_list(raw)
        hit = value in vals
        return hit if op == 'IN' else not hit
    v = _coerce_scalar(raw)
    try:
        if op == '=':
            return value == v
        if op == '!=':
            return value != v
        if value is None or v is None:
            return False
        if op == '>':
            return value > v
        if op == '<':
            return value < v
        if op == '>=':
            return value >= v
        if op == '<=':
            return value <= v
    except TypeError:
        try:
            if op == '=':
                return str(value) == str(v)
            if op == '!=':
                return str(value) != str(v)
        except Exception:
            pass
        return False
    return False


def _fmt_cell(value, cfg):
    from ajsystem.core.utils import fmt_money, fmt_date, fmt_datetime
    if value is None:
        return '—'
    cur = (cfg or {}).get('currency')
    if cur:
        from ajsystem.core.utils import normalize_currency
        code = normalize_currency(cur)
        return fmt_money(value, code if code is not None else 1)
    t = (cfg or {}).get('type')
    inp = (cfg or {}).get('input')
    if hasattr(value, 'strftime'):
        if t == 'DATA' or inp == 'date':
            return fmt_date(value)
        return fmt_datetime(value)
    if isinstance(value, float):
        s = f'{value:,.2f}'
        return s.replace(',', 'X').replace('.', ',').replace('X', '.')
    if hasattr(value, 'quantize'):
        s = format(value, 'f')
        if '.' in s:
            s = s.replace('.', ',')
            parts = s.split(',')
            parts[0] = f'{int(parts[0]):,}'.replace(',', '.')
            s = ','.join([parts[0], parts[1]])
        return s
    return str(value)


def _label_for(col, entity, src_entity):
    base = col.split('.')[-1]
    for ent in (entity, src_entity):
        cfg = (ent or {}).get(col, (ent or {}).get(base, None)) if ent else None
        if isinstance(cfg, dict) and cfg.get('label'):
            return cfg['label']
    from ajsystem.defs.data import _auto_label
    return _auto_label(base)


def _jsonable(v):
    """Valor cru JSON-safe p/ `replaces` (nulos/NaN viram None)."""
    import math
    if v is None or isinstance(v, (bool, int, str)):
        return v
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if hasattr(v, 'quantize'):
        try:
            f = float(v)
            return f if math.isfinite(f) else None
        except Exception:
            return str(v)
    if hasattr(v, 'isoformat'):
        try:
            return v.isoformat()
        except Exception:
            return str(v)
    return str(v)


def run_search(spec, params):
    """Executa uma busca declarada. `params` = args da request (str→str).

    Retorna `{'columns': [{'label'}], 'rows': [{'id', 'cells': [...]}, ...]}`
    ou `{'need': [...]}` quando faltam params exigidos.
    """
    from ajsystem.core.list import _resolve_model
    from ajsystem.core.query import order_items
    if not isinstance(spec, dict):
        return {'columns': [], 'rows': [], 'error': 'busca inválida'}
    model = _resolve_model(spec.get('source'))
    if model is None:
        return {'columns': [], 'rows': [], 'error': 'source desconhecido'}
    joins = spec.get('join')
    if isinstance(joins, str):
        joins = [joins]
    columns = spec.get('columns') or ['id']
    entity = _model_entity(model)

    # Params exigidos: {arg: dotted} — ausente/vazio → pede ao usuário.
    need = []
    param_conds = []
    for arg, path in (spec.get('params') or {}).items():
        v = (params or {}).get(arg)
        if v is None or (isinstance(v, str) and not v.strip()):
            need.append(arg)
            continue
        param_conds.append((path, '=', v))
    if need:
        return {'columns': [], 'rows': [], 'need': need}

    # Separa fixos SQL (coluna real) de computados (Python).
    sql_conds, py_conds = [], []
    joined = set()

    def _ensure_join(path):
        parts = (path or '').split('.')[:-1]
        for i in range(1, len(parts) + 1):
            joined.add('.'.join(parts[:i]))

    for raw in (spec.get('when') or []):
        parsed = _parse_cond(raw) if isinstance(raw, str) else None
        if parsed is None:
            continue
        path, op, rval = parsed
        _ensure_join(path)
        owner, attr = _split_dotted(model, path)
        # computado = `calc` na Entity ou nome sem coluna real (ex.: property)
        is_computed = False
        if '.' not in path:
            cfg = entity.get(path, {}) or {}
            if cfg.get('calc') is not None:
                is_computed = True
            else:
                try:
                    is_computed = model.__table__.columns.get(path) is None
                except Exception:
                    is_computed = True
        if is_computed:
            py_conds.append((path, op, rval))
        else:
            sql_conds.append((path, op, rval))
    for path, op, v in param_conds:
        _ensure_join(path)
        sql_conds.append((path, op, v))

    q = model.query
    for jp in sorted(joined):
        rel = jp.split('.')[0]
        try:
            q = q.join(getattr(model, rel), isouter=True)
        except Exception:
            pass
        try:
            from sqlalchemy.orm import joinedload
            q = q.options(joinedload(getattr(model, rel)))
        except Exception:
            pass
    for path, op, rval in sql_conds:
        c = _column_of(model, path)
        if c is None:
            continue
        cond = _sql_cond(c, op, rval, model)
        if cond is not None:
            q = q.filter(cond)
    try:
        rows = q.all()
    except Exception as e:
        return {'columns': [], 'rows': [], 'error': str(e)[:200]}

    out = []
    order = spec.get('order')
    if order:
        from ajsystem.core.utils import deep_attr as _da
        by = order if isinstance(order, list) else [order]
        for o in reversed(by):
            desc = isinstance(o, str) and o.strip().lower().endswith(' desc')
            oo = o[:-5].strip() if desc else o
            try:
                rows.sort(key=lambda r, _o=oo: (_da(r, _o) is None, _da(r, _o)), reverse=desc)
            except Exception:
                pass
    for row in rows:
        ok = True
        for path, op, rval in py_conds:
            if not _py_match(_py_val(row, path, entity), op, rval):
                ok = False
                break
        if not ok:
            continue
        cells = []
        raw = {}
        for col in columns:
            base = col.split('.')[-1]
            owner, attr = _split_dotted(model, col)
            cfg = {}
            try:
                if owner is not None and hasattr(owner, '__table__'):
                    cfg = _model_entity(owner).get(attr, {}) or {}
            except Exception:
                cfg = {}
            if not cfg:
                cfg = entity.get(col, entity.get(base, {}) or {}) or {}
            v = _py_val(row, col, entity)
            cells.append(_fmt_cell(v, cfg))
            raw[base] = _jsonable(v)
        rid = getattr(row, 'id', None)
        out.append({'id': rid, 'cells': cells, 'raw': raw})

    labels = []
    for col in columns:
        base = col.split('.')[-1]
        owner, attr = _split_dotted(model, col)
        ent = {}
        try:
            if owner is not None and hasattr(owner, '__table__'):
                ent = _model_entity(owner)
        except Exception:
            ent = {}
        labels.append({'label': _label_for(col, ent, entity)})
    return {'columns': labels, 'rows': out}
