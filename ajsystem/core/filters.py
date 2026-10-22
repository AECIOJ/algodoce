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

DEFAULT_FILTER_MAX_WIDTH = '88ch'
MAX_FILTER_ROWS = 128
MAX_FILTER_BLOCKS = 32


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


def _row(name, conn, value):
    """Uma linha do builder de filtros: campo, conector e valor."""
    return {'f': name, 'c': conn, 'v': value}


def _parse_leaf(config, item, label):
    """Valida uma linha `{f,c,v}` do builder; `label` já nomeia o índice."""
    if not isinstance(item, dict) or not item.get('f'):
        raise ValueError(f"{label} sem campo ('f')")
    name = item['f']
    if name not in config:
        raise ValueError(
            f"{label} campo {name!r} não está no painel de filtros")
    conn = item.get('c') or 'and'
    if conn not in ('and', 'or'):
        raise ValueError(
            f"{label} conector {conn!r} inválido — use 'and'/'or'")
    return _row(name, conn, item.get('v'))


def parse_json_rows(config, raw, where='list.filter', arg='_f'):
    """Linhas do builder a partir de um JSON ordenado `[{f,c,v}, ...]`.

    Usado pelo PADRÃO (`_df`) e pelo formato legado de `_f`: campo fora do
    painel, conector inválido ou JSON malformado levantam erro nomeando o arg
    e o índice. O bloco do usuário novo é lido por `parse_json_blocks`.
    """
    import json
    try:
        data = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{where}: {arg} não é JSON válido ({exc})") from exc
    if not isinstance(data, list):
        raise ValueError(f"{where}: {arg} esperava uma lista de linhas")
    if len(data) > MAX_FILTER_ROWS:
        raise ValueError(
            f"{where}: {arg} tem mais de {MAX_FILTER_ROWS} linhas")
    return [
        _parse_leaf(config, item, f"{where}: {arg}[{i}]")
        for i, item in enumerate(data)
    ]


def parse_json_blocks(config, raw, where='list.filter', arg='_f'):
    """Blocos do usuário a partir de `_f` (formato novo ou legado).

    Formato novo: `[{"c": "and", "g": true, "rows": [{f,c,v}, ...]}, ...]`.
    `c` é o elo do bloco com o bloco anterior (o primeiro elo liga ao PADRÃO).
    `g` é só visual: `false` marca uma linha solta (sem parênteses) e `true`
    um bloco agrupado; ausente vale `true` para manter o formato antigo. O
    formato antigo, uma lista plana de linhas, continua válido e vira **um**
    bloco com o mesmo conector da primeira linha — parênteses em volta de todas
    as linhas não mudam a expressão. Bloco vazio, mistura de blocos/linhas,
    conector inválido, `g` não booleano e limites levantam erro nomeando o
    índice.
    """
    import json
    try:
        data = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{where}: {arg} não é JSON válido ({exc})") from exc
    if not isinstance(data, list):
        raise ValueError(f"{where}: {arg} esperava uma lista de blocos")
    if not data:
        return []
    has_blocks = any(isinstance(item, dict) and 'rows' in item for item in data)
    if not has_blocks:
        rows = [
            _parse_leaf(config, item, f"{where}: {arg}[{i}]")
            for i, item in enumerate(data)
        ]
        if len(rows) > MAX_FILTER_ROWS:
            raise ValueError(
                f"{where}: {arg} tem mais de {MAX_FILTER_ROWS} linhas")
        return [{'c': rows[0].get('c') or 'and', 'g': True, 'rows': rows}]

    blocks = []
    total = 0
    for i, item in enumerate(data):
        if not isinstance(item, dict) or 'rows' not in item:
            raise ValueError(
                f"{where}: {arg}[{i}] mistura blocos e linhas")
        raw_rows = item.get('rows')
        if not isinstance(raw_rows, list):
            raise ValueError(
                f"{where}: {arg}[{i}].rows esperava uma lista de linhas")
        if not raw_rows:
            raise ValueError(f"{where}: {arg}[{i}] bloco vazio")
        conn = item.get('c') or 'and'
        if conn not in ('and', 'or'):
            raise ValueError(
                f"{where}: {arg}[{i}] conector {conn!r} inválido — "
                "use 'and'/'or'")
        grouped = item.get('g', True)
        if not isinstance(grouped, bool):
            raise ValueError(
                f"{where}: {arg}[{i}].g esperava booleano")
        rows = [
            _parse_leaf(config, row, f"{where}: {arg}[{i}].rows[{j}]")
            for j, row in enumerate(raw_rows)
        ]
        total += len(rows)
        if total > MAX_FILTER_ROWS:
            raise ValueError(
                f"{where}: {arg} tem mais de {MAX_FILTER_ROWS} linhas")
        blocks.append({'c': conn, 'g': grouped, 'rows': rows})
    if len(blocks) > MAX_FILTER_BLOCKS:
        raise ValueError(
            f"{where}: {arg} tem mais de {MAX_FILTER_BLOCKS} blocos")
    return blocks


def parse_blocks(config, request_args, where='list.filter'):
    """Blocos do usuário a partir da URL; sem `_f`, monta o fallback em E."""
    raw = request_args.get('_f')
    if raw not in (None, ''):
        return parse_json_blocks(config, raw, where, '_f')
    rows = []
    for name, cfg in config.items():
        val = _active_from_args(cfg.get('type'), name, request_args)
        if val is not None:
            rows.append(_row(name, 'and', val))
    return [{'c': 'and', 'g': True, 'rows': rows}] if rows else []


def default_expression_rows(expr, resolve_name, where='list.filter.default',
                            max_rows=128):
    """`filter.default` (dict ou `OR`/`AND`) → linhas DNF do builder.

    Um dict é AND das folhas (formato antigo, compatível); `OR(...)`/`AND(...)`
    agrupam e o AND **distribui** sobre o OR, porque o painel só sabe representar
    DNF (grupos de AND ligados por OR). Cada folha mapeia campo → valor de
    filtro (não literal, ao contrário de `fixed`).
    """
    from ajsystem.defs.constants import _Grupo

    def dnf(node, path):
        if isinstance(node, _Grupo):
            parts = [dnf(it, f'{path}.{node.op}') for it in node.itens]
            if node.op == 'or':
                return [c for p in parts for c in p]
            out = [[]]
            for p in parts:
                out = [a + b for a in out for b in p]
                if len(out) > max_rows:
                    raise ValueError(
                        f"{where}: {path} gera mais de {max_rows} linhas ao "
                        "distribuir AND sobre OR — simplifique o default")
            return out
        if isinstance(node, dict):
            if not node:
                raise ValueError(f"{where}: grupo vazio em {path}")
            return [[(resolve_name(k), v) for k, v in node.items()]]
        raise TypeError(
            f"{where}: {path} esperava dict ou OR(...)/AND(...); "
            f"veio {type(node).__name__}")

    combos = dnf(expr, 'default')
    rows = []
    for i, combo in enumerate(combos):
        for j, (name, value) in enumerate(combo):
            rows.append(_row(name, 'or' if (i > 0 and j == 0) else 'and', value))
    if len(rows) > max_rows:
        raise ValueError(
            f"{where}: default gera mais de {max_rows} linhas — simplifique")
    return rows


def default_rows(config, defaults):
    """Linhas iniciais (`filter.default`) validadas contra o painel."""
    if isinstance(defaults, dict):
        defaults = [_row(name, 'and', value) for name, value in defaults.items()]
    rows = []
    for row in defaults or []:
        name = row.get('f')
        if name not in config:
            raise ValueError(
                f"filter.default: campo {name!r} não está no painel de filtros "
                "— só colunas filtráveis aceitam um valor inicial")
        conn = row.get('c') or 'and'
        if conn not in ('and', 'or'):
            raise ValueError(
                f"filter.default: conector {conn!r} inválido — use 'and'/'or'")
        rows.append(_row(name, conn, row.get('v')))
    return rows


def resolve_filters(config, request_args, defaults=None, where='list.filter'):
    """Linhas do painel: `(declarado, padrão efetivo, usuário, ligado?)`.

    `defaults` são as linhas de `filter.default` (já normalizadas pela spec).
    O padrão nasce **ligado**; `_d=0` desliga. `_df` carrega o padrão editado
    em memória e só vale com o padrão ligado. `active` são **apenas** os blocos
    do usuário (`_f`/legado) — o `resolve_filter` liga o PADRÃO ao primeiro
    bloco efetivo pelo conector desse bloco.
    """
    initial = default_rows(config, defaults)
    has_default = bool(initial)
    raw_d = request_args.get('_d')
    default_on = has_default and str(raw_d).lower() not in ('0', 'false', 'off', 'no')
    if default_on and '_df' in request_args:
        edited = parse_json_rows(config, request_args.get('_df'),
                                 f'{where}.default', '_df')
    else:
        edited = [dict(r) for r in initial]
    active = parse_blocks(config, request_args, where)
    return initial, edited, active, default_on


def _row_conds(row, config, model, resolve, where='list.filter'):
    """Condições SQL de uma linha do builder (vazio se o campo não resolve)."""
    name = row.get('f')
    cfg = config.get(name)
    if cfg is None:
        return []
    col = resolve(model, name)
    if col is None:
        return []
    ftype = cfg.get('type')
    if ftype == 'date':
        return _date_conds(col, row.get('v'))
    return _filter_conditions(col, ftype, row.get('v')) or []


def rows_condition(rows, config, model, attr_resolver=None, where='list.filter'):
    """Linhas do builder → uma expressão SQL (AND tem prioridade sobre OR).

    ANDs consecutivos formam um grupo; cada `or` abre um grupo novo. O
    resultado é `or_(and_(...), and_(...))` — `a AND b OR c` = `(a AND b) OR c`,
    a mesma leitura do `compile_fixed`.
    """
    if not rows:
        return None
    resolve = attr_resolver if attr_resolver is not None else (
        lambda m, f: getattr(m, f, None))
    groups = []
    for row in rows:
        conds = _row_conds(row, config, model, resolve, where)
        if not conds:
            continue
        if row.get('c') == 'or' or not groups:
            groups.append(list(conds))
        else:
            groups[-1].extend(conds)
    parts = [and_(*g) if len(g) > 1 else g[0] for g in groups]
    if not parts:
        return None
    return parts[0] if len(parts) == 1 else or_(*parts)


def blocks_condition(blocks, config, model, attr_resolver=None,
                     where='list.filter'):
    """Blocos do usuário → uma expressão SQL (E tem prioridade sobre OU).

    Cada bloco é um operando: as linhas internas são compiladas por
    `rows_condition` (primeiro conector ignorado) e os blocos são combinados
    pelo `c` do próprio bloco. O primeiro `c` do root é ignorado aqui — quem
    liga o primeiro bloco ao PADRÃO é o `resolve_filter`.
    """
    if not blocks:
        return None
    groups = []
    for block in blocks:
        cond = rows_condition(block.get('rows') or [], config, model,
                              attr_resolver, where)
        if cond is None:
            continue
        if block.get('c') == 'or' or not groups:
            groups.append([cond])
        else:
            groups[-1].append(cond)
    parts = [and_(*g) if len(g) > 1 else g[0] for g in groups]
    if not parts:
        return None
    return parts[0] if len(parts) == 1 else or_(*parts)


def first_block_conn(blocks, config, model, attr_resolver=None,
                     where='list.filter'):
    """Conector do primeiro bloco que realmente produz condição (ou `and`)."""
    for block in blocks or []:
        if rows_condition(block.get('rows') or [], config, model,
                          attr_resolver, where) is not None:
            return block.get('c') or 'and'
    return 'and'


@dataclass
class ResolvedFilter:
    """Prop `filter` da listagem resolvida num lugar só (§5.6).

    `hidden`/`types` alimentam o painel; `default` são as linhas declaradas do
    filtro inicial; `fixed` são as condições SQL fixas já compiladas.
    `initial`/`default_filters` são as linhas do PADRÃO (declarado e efetivo
    editado via `_df`); `active` são os **blocos** do usuário. `filter_cond` é
    a condição SQL única — PADRÃO ligado ao bloco do usuário pelo conector do
    primeiro bloco efetivo (E por padrão; OU quando ele é `or`). `default_on`
    diz se o bloco padrão entra.
    `panel`/`initial`/... só são preenchidos quando `resolve_filter` recebe
    `fields` (render da lista); sem `fields` (guarda de escopo do form) ficam
    `None`.
    """
    hidden: set = field(default_factory=set)
    fixed: list = field(default_factory=list)
    default: list = field(default_factory=list)
    types: dict = field(default_factory=dict)
    panel: dict = None
    initial: list = None
    default_filters: list = None
    active: list = None
    default_on: bool = False
    max_width: str = None
    filter_cond: object = None


def resolve_filter(spec, *, pool, principal=None, model=None, attr_resolver=None,
                   fields=None, request_args=None, where='list.filter'):
    """Ponto único de entrada da prop `filter` (`fixed` + `default` + resto).

    Resolve a spec contra o `pool` (`resolve_filter_spec`), compila o `fixed`
    contra o `model` (`compile_fixed`) e — se `fields` é dado — monta o painel
    (`build_filter_config`), as linhas declaradas/padrão/usuário
    (`resolve_filters`) e a condição SQL do PADRÃO ligado ao bloco do usuário
    pelo conector do primeiro bloco efetivo (E por padrão, OU se ele for `or`)
    (`blocks_condition`). Sem `fields`, serve só à guarda de escopo
    (`core.do_form`), que precisa do `fixed`.

    `max_width` ausente cai no default interno `DEFAULT_FILTER_MAX_WIDTH`
    (`88ch`); o valor declarado pelo app (int → `ch`, ou string CSS) vence.
    """
    from ajsystem.core.list import build_filter_config, resolve_filter_spec
    from ajsystem.defs.data import resolve_max_width
    spec = spec or {}
    hidden, fixed_spec, default, types = resolve_filter_spec(
        spec, pool, principal, where)
    fixed = (compile_fixed(fixed_spec, model, attr_resolver, f'{where}.fixed')
             if model is not None else [])
    raw_max_width = spec.get('max_width')
    if raw_max_width is None:
        raw_max_width = DEFAULT_FILTER_MAX_WIDTH
    try:
        max_width = resolve_max_width(raw_max_width)
    except ValueError as exc:
        raise ValueError(f"{where}.max_width: {exc}") from exc
    rf = ResolvedFilter(hidden=hidden, fixed=fixed, default=default, types=types,
                        max_width=max_width)
    if fields is not None:
        rf.panel = build_filter_config(fields, hidden=hidden, types=types)
        (rf.initial, rf.default_filters, rf.active,
         rf.default_on) = resolve_filters(
            rf.panel, request_args or {}, defaults=default, where=where)
        if model is not None:
            default_cond = rows_condition(
                rf.default_filters if rf.default_on else [],
                rf.panel, model, attr_resolver, f'{where}.default')
            user_cond = blocks_condition(
                rf.active, rf.panel, model, attr_resolver, where)
            if default_cond is not None and user_cond is not None:
                # O conector do primeiro bloco efetivo do usuário liga o root
                # ao PADRÃO. `blocks_condition` já ignora esse conector dentro
                # do root, então usá-lo aqui não o aplica duas vezes. Sem
                # default, ele continua sem efeito.
                block_conn = first_block_conn(
                    rf.active, rf.panel, model, attr_resolver, where)
                if block_conn == 'or':
                    rf.filter_cond = or_(default_cond, user_cond)
                else:
                    rf.filter_cond = and_(default_cond, user_cond)
            else:
                rf.filter_cond = (default_cond if default_cond is not None
                                  else user_cond)
    return rf


def _as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        from datetime import datetime as _dt
        for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
            try:
                return _dt.strptime(value.strip(), fmt).date()
            except ValueError:
                pass
    return None


def _as_int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _date_conds(col, cfg, hoje=None):
    """Condições SQL do filtro de data (`date`), por preset.

    `Mês atual`/`Mês anterior` olham **só o mês** (aniversariantes: o ano não
    importa); `Mês/Ano atual`/`Mês/Ano anterior` olham mês **e** ano
    (vencimentos). O preset com valor vazio devolve `[]` (linha sem condição).
    """
    if not isinstance(cfg, dict):
        return []
    hoje = hoje or date.today()
    preset = cfg.get('preset')
    if not preset:
        return []
    if preset == 'hoje':
        return [col == hoje]
    if preset == 'ontem':
        return [col == hoje - timedelta(days=1)]
    if preset == 'ultimos_7_dias':
        return [col >= hoje - timedelta(days=6), col <= hoje]
    if preset in ('mes_atual', 'mes_anterior'):
        ref = hoje if preset == 'mes_atual' else (hoje.replace(day=1) - timedelta(days=1))
        return [extract('month', col) == ref.month]
    if preset in ('mes_ano', 'mes_ano_anterior'):
        if preset == 'mes_ano':
            mes, ano = _as_int(cfg.get('mes')), _as_int(cfg.get('ano'))
            if mes is None:
                mes = hoje.month
            if ano is None:
                ano = hoje.year
        else:
            ref = hoje.replace(day=1) - timedelta(days=1)
            mes = _as_int(cfg.get('mes')) or ref.month
            ano = _as_int(cfg.get('ano')) or ref.year
        if not (1 <= mes <= 12):
            return []
        return [extract('month', col) == mes, extract('year', col) == ano]
    if preset in ('ano_atual', 'ano_anterior'):
        ano = hoje.year if preset == 'ano_atual' else hoje.year - 1
        return [extract('year', col) == ano]
    if preset == 'mes':
        mes = _as_int(cfg.get('mes'))
        return [extract('month', col) == mes] if mes and 1 <= mes <= 12 else []
    if preset == 'ano':
        ano = _as_int(cfg.get('ano'))
        return [extract('year', col) == ano] if ano else []
    if preset == 'a_partir_de':
        d = _as_date(cfg.get('from'))
        return [col >= d] if d else []
    if preset == 'ate_a_data_de':
        d = _as_date(cfg.get('to'))
        return [col <= d] if d else []
    if preset == 'periodo':
        d1, d2 = _as_date(cfg.get('from')), _as_date(cfg.get('to'))
        conds = []
        if d1:
            conds.append(col >= d1)
        if d2:
            conds.append(col <= d2)
        return conds
    return []


def filtrar_vencimento_query(query, model_field, preset, hoje=None):
    """DEPRECADO — aplica `_date_conds` numa query (compatibilidade)."""
    for cond in _date_conds(model_field, {'preset': preset}, hoje=hoje):
        query = query.filter(cond)
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
