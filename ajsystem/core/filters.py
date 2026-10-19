"""FILTERS — resolução e aplicação de filtros de listagem.

Reescrito do zero observando `core/old/filters.py`. `resolve_filters` produz a
estrutura consumida por `pages/list.html` (`initial_filters`/`active_filters`).
`apply_filters` aplica condições no nível SQL quando aplicável.
"""
import calendar
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy import Integer as _Integer
from sqlalchemy import and_, extract, func, or_


def _active_from_args(ftype, name, request_args):
    """Valor ativo de um filtro a partir dos query args, ou `None` se ausente."""
    av = request_args.get(name)
    if av not in (None, ''):
        if ftype == 'checklist':
            # checklist: comma-separated string → list para Alpine x-model
            if isinstance(av, str):
                return [v.strip() for v in av.split(',') if v.strip() != '']
            if isinstance(av, (list, tuple)):
                return [str(v) for v in av if str(v).strip() != '']
            return [str(av)]
        return av
    if ftype == 'number':
        v1 = request_args.get(f'{name}_val1')
        if v1 in (None, ''):
            return None
        return {'mode': request_args.get(f'{name}_mode', 'igual'),
                'val1': v1, 'val2': request_args.get(f'{name}_val2') or ''}
    if ftype == 'date':
        preset = request_args.get(f'{name}_preset')
        if not preset:
            return None
        entry = {'preset': preset}
        for k in ('from', 'to', 'mes', 'ano'):
            v = request_args.get(f'{name}_{k}')
            if v:
                entry[k] = v
        return entry
    if ftype == 'text':
        value = request_args.get(f'{name}_value')
        if value in (None, ''):
            return None
        return {'mode': request_args.get(f'{name}_mode', 'contains'), 'value': value}
    return None


def resolve_filters(config, request_args, defaults=None):
    """Gera (initial_filters, active_filters) a partir do config e query args.

    `defaults` é o `filter.default` da página (`{campo: valor}`): quando o
    argumento não vem na URL, o valor vira o inicial **e** o ativo — então o
    filtro nasce aplicado, o usuário pode editar e, ao limpar, ele volta.
    O campo tem que estar no painel (`config`); um nome fora dele é erro.
    """
    defaults = defaults or {}
    initial = {}
    active = {}
    for name in defaults:
        if name not in config:
            raise ValueError(
                f"filter.default: campo {name!r} não está no painel de filtros "
                "— só colunas filtráveis aceitam um valor inicial")
    for name, cfg in config.items():
        ftype = cfg.get('type')
        if ftype == 'checklist':
            initial[name] = []
        elif ftype in ('select', 'boolean'):
            initial[name] = ''
        elif ftype == 'date':
            initial[name] = {'preset': ''}
        elif ftype == 'number':
            initial[name] = {'mode': 'igual', 'val1': '', 'val2': ''}
        else:
            initial[name] = {'mode': 'contains', 'value': ''}

        val = _active_from_args(ftype, name, request_args)
        if val is not None:
            active[name] = val
        elif name in defaults:
            initial[name] = defaults[name]
            active[name] = defaults[name]
    return initial, active


@dataclass
class ResolvedFilter:
    """Prop `filter` da listagem resolvida num lugar só (§5.6).

    `hidden`/`types` alimentam o painel; `default` é o filtro inicial editável;
    `fixed` são as condições SQL fixas já compiladas. `panel`/`initial`/`active`
    só são preenchidos quando `resolve_filter` recebe `fields` (render da lista);
    sem `fields` (guarda de escopo do form) ficam `None`.
    """
    hidden: set = field(default_factory=set)
    fixed: list = field(default_factory=list)
    default: dict = field(default_factory=dict)
    types: dict = field(default_factory=dict)
    panel: dict = None
    initial: dict = None
    active: dict = None


def resolve_filter(spec, *, pool, principal=None, model=None, attr_resolver=None,
                   fields=None, request_args=None, where='list.filter'):
    """Ponto único de entrada da prop `filter` (`fixed` + `default` + resto).

    Resolve a spec contra o `pool` (`resolve_filter_spec`), compila o `fixed`
    contra o `model` (`compile_fixed`) e — se `fields` é dado — monta o painel
    (`build_filter_config`) e o estado inicial/ativo (`resolve_filters`). Sem
    `fields`, serve só à guarda de escopo (`core.do_form`), que precisa do
    `fixed`.
    """
    from ajsystem.core.list import build_filter_config, resolve_filter_spec
    hidden, fixed_spec, default, types = resolve_filter_spec(
        spec, pool, principal, where)
    fixed = (compile_fixed(fixed_spec, model, attr_resolver, f'{where}.fixed')
             if model is not None else [])
    rf = ResolvedFilter(hidden=hidden, fixed=fixed, default=default, types=types)
    if fields is not None:
        rf.panel = build_filter_config(fields, hidden=hidden, types=types)
        rf.initial, rf.active = resolve_filters(
            rf.panel, request_args or {}, defaults=default)
    return rf


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


def _key(value):
    """Coage chave de filtro `select`: string numérica → int; resto intacto.

    O filtro submete a CHAVE das options (ex.: `'1'`), não o rótulo.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and re.fullmatch(r'[+-]?\d+', value.strip() or ''):
        try:
            return int(value.strip())
        except (TypeError, ValueError):
            pass
    return value


def fixed_filters(spec, model, attr_resolver=None, where='list.filter.fixed'):
    """DEPRECADO — alias de `compile_fixed` (mantido por compatibilidade)."""
    return compile_fixed(spec, model, attr_resolver, where)


_OPS_LEAF = {
    '=': lambda c, v: c == v,
    '!=': lambda c, v: c != v,
    '>': lambda c, v: c > v,
    '>=': lambda c, v: c >= v,
    '<': lambda c, v: c < v,
    '<=': lambda c, v: c <= v,
    'like': lambda c, v: c.like(v),
    'ilike': lambda c, v: c.ilike(v),
}


def _is_textual(col):
    from sqlalchemy import String as _String
    return isinstance(getattr(col, 'type', None), _String)


def _empty_cond(col, negate=False):
    """`EMPTY`/`NOT_EMPTY` — casa `is_empty` (`None`, branco ou coleção vazia).

    Coluna textual soma `trim(col) = ''` (espelha o `.strip()` de `is_empty`);
    nas demais, o vazio é só `IS NULL`.
    """
    cond = col.is_(None)
    if _is_textual(col):
        cond = or_(cond, func.trim(col) == '')
    return ~cond if negate else cond


def _leaf_cond(col, value, where='list.filter.fixed'):
    """Condição SQL de uma folha `<campo>: <valor>`; `None` manda ignorar.

    Vocabulário do valor: literal → `=`; `NULL`/`NOT_NULL` → `IS [NOT] NULL`;
    `EMPTY`/`NOT_EMPTY` → `is_empty`/`not is_empty`; `('op', valor)` com `op` em
    `_OPS_LEAF`/`in`/`not in`; lista/tupla/set → `IN`; callable (resolvido antes);
    `None` → ignora a folha.
    """
    from ajsystem.defs.constants import EMPTY, NOT_EMPTY, NOT_NULL, NULL
    if value is None:
        return None
    if value is NULL:
        return col.is_(None)
    if value is NOT_NULL:
        return col.isnot(None)
    if value is EMPTY:
        return _empty_cond(col, negate=False)
    if value is NOT_EMPTY:
        return _empty_cond(col, negate=True)
    if isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], str):
        op = value[0].strip().lower()
        operand = value[1]
        if op in ('in', 'not in'):
            seq = operand if isinstance(operand, (list, tuple, set, frozenset)) else [operand]
            vals = [v for v in seq if v is not None]
            if not vals:
                return None
            return col.in_(vals) if op == 'in' else ~col.in_(vals)
        fn = _OPS_LEAF.get(op)
        if fn is None:
            raise ValueError(
                f"{where}: operador {value[0]!r} desconhecido — use "
                f"{', '.join(sorted(_OPS_LEAF))}, 'in'/'not in'")
        return fn(col, operand)
    if isinstance(value, (list, tuple, set, frozenset)):
        vals = [v for v in value if v is not None]
        return col.in_(vals) if vals else None
    return col == _key(value)


def _compile_node(node, model, resolve, where):
    from ajsystem.defs.constants import _Grupo
    if isinstance(node, _Grupo):
        conds = [c for c in (_compile_node(it, model, resolve, where)
                             for it in node.itens) if c is not None]
        if not conds:
            return None
        return or_(*conds) if node.op == 'or' else and_(*conds)
    if isinstance(node, dict):
        conds = []
        for name, value in node.items():
            value = value() if callable(value) else value
            if value is None:
                continue
            col = resolve(model, name)
            if col is None:
                raise ValueError(
                    f"{where}: {name!r} não é coluna de {model.__name__}")
            leaf = _leaf_cond(col, value, where)
            if leaf is not None:
                conds.append(leaf)
        if not conds:
            return None
        return conds[0] if len(conds) == 1 else and_(*conds)
    raise TypeError(f"{where}: esperava dict ou OR(...)/AND(...); veio "
                    f"{type(node).__name__}")


def compile_fixed(spec, model, attr_resolver=None, where='list.filter.fixed'):
    """`list.filter.fixed` (dict de folhas ou `OR(...)`/`AND(...)`) → condições.

    Um dict é AND das folhas; `OR(...)`/`AND(...)` agrupam (aninháveis). O dict
    é o caso comum (AND implícito). `attr_resolver` atravessa a relação filho→pai
    na inversão (`master`). Folha cujo valor é `None` é ignorada; nome que não
    é coluna do model levanta erro nomeando (nada some em silêncio).
    """
    if not spec:
        return []
    resolve = attr_resolver if attr_resolver is not None else (
        lambda m, f: getattr(m, f, None))
    cond = _compile_node(spec, model, resolve, where)
    return [cond] if cond is not None else []


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
        is_int = isinstance(getattr(model_field, 'type', None), _Integer)
        from sqlalchemy import Boolean as _Boolean
        is_bool = isinstance(getattr(model_field, 'type', None), _Boolean)
        # checklist pode vir como list (do resolve_filters) ou string "0,1"
        if isinstance(cfg_value, (list, tuple)):
            vals = []
            for v in cfg_value:
                # boolean checklist: "true"/"false" → True/False
                if is_bool and isinstance(v, str):
                    lv = v.strip().lower()
                    if lv == 'true':
                        vals.append(True)
                        continue
                    if lv == 'false':
                        vals.append(False)
                        continue
                v = _key(str(v).strip()) if isinstance(v, str) else _key(v)
                if is_int and isinstance(v, str):
                    continue
                vals.append(v)
            return [model_field.in_(vals)] if vals else []
        if isinstance(cfg_value, str) and ',' in cfg_value:
            vals = []
            for v in cfg_value.split(','):
                v = v.strip()
                if not v:
                    continue
                if is_bool:
                    lv = v.lower()
                    if lv == 'true':
                        vals.append(True)
                        continue
                    if lv == 'false':
                        vals.append(False)
                        continue
                v = _key(v)
                if is_int and isinstance(v, str):
                    continue  # rótulo/lixo em coluna int: ignora em vez de 500
                vals.append(v)
            return [model_field.in_(vals)] if vals else []
        if cfg_value or cfg_value == 0 or cfg_value is False:
            # para checklist com um único valor (string sem vírgula) ou select
            if is_bool and isinstance(cfg_value, str):
                lv = cfg_value.strip().lower()
                if lv == 'true':
                    return [model_field == True]  # noqa: E712
                if lv == 'false':
                    return [model_field == False]  # noqa: E712
            v = _key(cfg_value)
            if is_int and isinstance(v, str):
                return []
            return [model_field == v]
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
