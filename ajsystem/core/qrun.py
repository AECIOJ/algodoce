"""QRun — executor genérico de QuerySpec/OverSpec (SQL filtra, janela numera).

Genérico: não cita entidade do app. Recebe model + QuerySpec + entity_cfg
({campo: cfg} p/ cast) e devolve linhas (instâncias + attrs computados).

Fase 1: WHERE/ORDER/LIMIT/GROUP BY no SQL; OVER avaliado em passo único
em Python sobre o resultado (1 query, sem N+1). `where`/`extra_where` usam
a gramática literal dos filtros (AND/OR/sentinelas/operadores); `extra_conditions`
recebe condições já compiladas. O filtro entra antes dos OVERs.
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


def _resolve_column(model, field_name):
    """Resolve um campo, tentando também através de relationships (join).
    
    Para campos de models relacionados (join), retorna a coluna através
    do relationship: model.relacionamento.campo.
    """
    # Tentar diretamente no model
    col = getattr(model, field_name, None)
    if col is not None and hasattr(col, 'type'):
        return col
    
    # Tentar através de relationships (join)
    # Ex: 'conta_id' pode estar em 'transacao.conta_id'
    if hasattr(model, '__mapper__'):
        for rel_name in model.__mapper__.relationships.keys():
            rel = getattr(model, rel_name, None)
            if rel is not None:
                try:
                    mapper_cls = rel.property.mapper.class_
                    col = getattr(mapper_cls, field_name, None)
                    if col is not None and hasattr(col, 'type'):
                        # Retornar a coluna através do relationship
                        return getattr(rel, field_name, None) or col
                except Exception:
                    pass
    
    return None


def apply_where(query, model, where, entity_cfg):
    """Aplica um spec de WHERE na gramática compartilhada dos filtros.

    Aceita dict/lista (AND implícito), `OR(...)`/`AND(...)`, sentinelas e
    operadores — a mesma gramática de `filter.fixed` e `body.filter`.
    O valor é convertido pelo tipo do field via `_cast_value` (exceto
    `like`/`ilike`, que recebem o padrão textual).
    """
    if not where:
        return query
    from ajsystem.core.filters import compile_conditions
    cfg = entity_cfg or {}
    cast = lambda name, value: _cast_value(cfg.get(name, {}), value)
    
    # Resolver campos através de relationships (join)
    def _resolve(m, f):
        col = _resolve_column(m, f)
        if col is not None:
            return col
        return getattr(m, f, None)
    
    conds = compile_conditions(where, model, resolve=_resolve, cast=cast, where='query.where')
    for cond in conds:
        query = query.filter(cond)
    return query



def _normalize_joins(join_spec):
    """Normaliza a especificação de join para uma lista de dicts padronizados.
    
    Formatos aceitos:
    - str: 'tabela' -> left join, alias = primeira letra
    - dict: {'relation': 'tabela', 'type': 'left', 'as': 't', 'on': 'p.id = t.id'}
    - list: ['tabela', {'relation': 'outra_tabela', 'type': 'full', 'as': 'tx'}]
    """
    if join_spec is None:
        return []
    if isinstance(join_spec, str):
        return [{'relation': join_spec, 'type': 'left', 'as': join_spec[0].lower()}]
    elif isinstance(join_spec, dict):
        # Dict simples: {'relation': 'tabela', 'as': 'tx'}
        if 'relation' in join_spec and 'as' not in join_spec:
            return [{'relation': join_spec['relation'], 'type': 'left', 'as': join_spec.get('as', join_spec['relation'][0].lower())}]
        # Dict completo
        return [join_spec]
    elif isinstance(join_spec, list):
        results = []
        for item in join_spec:
            if isinstance(item, str):
                results.append({'relation': item, 'type': 'left', 'as': item[0].lower()})
            elif isinstance(item, dict):
                results.append(item)
        return results
    return []


def _apply_join(query, model, join_spec, entity_cfg=None):
    """Aplica um join ao query SQLAlchemy.
    
    join_spec: dict com chaves:
        - relation: nome do relationship no model
        - type: 'left'|'inner'|'right'|'full' (default: 'left')
        - as: alias para o model juntado
        - on: condição ON personalizada (opcional)
    """
    relation = join_spec.get('relation')
    if not relation:
        return query
    
    type_join = join_spec.get('type', 'left')
    is_outer = (type_join == 'left')
    
    try:
        # Get the relationship from the model
        rel_attr = getattr(model, relation)
        # Apply the join
        query = query.join(rel_attr, isouter=is_outer)
    except Exception:
        pass
    
    return query



def _resolve_join_path_for_query(query, model, field_name):
    """Aplica joins automáticos para um campo possivelmente pontilhado.

    Ex: 'conta.nome' em Previsao -> faz left join em Previsao.conta e
    retorna (query, Conta, 'nome'), de modo que a ordenação possa usar
    a coluna direta do model alvo. Se não conseguir resolver, devolve
    (query, model, field_name) inalterado.
    """
    if '.' not in field_name:
        return query, model, field_name

    parts = field_name.split('.')
    current_query = query
    current_model = model

    for part in parts[:-1]:
        rel_attr = getattr(current_model, part, None)
        if rel_attr is None:
            return current_query, current_model, field_name
        try:
            target_model = rel_attr.property.mapper.class_
        except Exception:
            return current_query, current_model, field_name
        try:
            current_query = current_query.join(rel_attr, isouter=True)
        except Exception:
            pass
        current_model = target_model

    col = getattr(current_model, parts[-1], None)
    if col is not None and hasattr(col, 'type'):
        return current_query, current_model, parts[-1]

    return current_query, current_model, field_name


def _resolve_path_model(model, field_name):
    """Resolve o model alvo de um caminho pontilhado sem aplicar join.

    Ex: 'conta.nome' em Previsao -> retorna (Conta, 'nome').
    Usado apenas para obter o model correto; o join já foi aplicado antes.
    """
    if '.' not in field_name:
        return model, field_name

    parts = field_name.split('.')
    current_model = model

    for part in parts[:-1]:
        rel_attr = getattr(current_model, part, None)
        if rel_attr is None:
            return current_model, field_name
        try:
            current_model = rel_attr.property.mapper.class_
        except Exception:
            return current_model, field_name

    col = getattr(current_model, parts[-1], None)
    if col is not None and hasattr(col, 'type'):
        return current_model, parts[-1]

    return current_model, field_name


def _order_cols(query, model, order):
    cols = []
    if not order:
        return cols, query
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
        # Resolver o model alvo para campos pontilhados (join já foi aplicado antes)
        _m, _fname = _resolve_path_model(model, fname)
        col = getattr(_m, _fname, None)
        if col is not None:
            cols.append(col.desc().nullslast() if desc else col.asc().nullsfirst())
    return cols, query


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
    """calc referencia coluna do model ou entrada over/agg — nunca outro calc
    (a ordem do select é de exibição; avaliação é over -> calc, sem cadeia)."""
    import re as _re
    cols = set(getattr(model, '__table__', None).columns.keys()) if getattr(model, '__table__', None) is not None else set()
    calcs = {e.name for e in entries or [] if e.calc}
    known = cols | {e.name for e in entries or []}
    for e in entries or []:
        if not e.calc:
            continue
        for nm in set(_re.findall(r'{\??(\w+)', e.calc)):
            if nm not in known:
                raise ValueError(f"select '{e.name}': calc referencia campo desconhecido '{nm}'")
            if nm in calcs:
                raise ValueError(f"select '{e.name}': calc não pode referenciar outro calc ('{nm}')")


def _eval_key(row, key, entries=None):
    """Avalia 1 chave normalizada ('field'| 'expr') sobre a linha."""
    from ajsystem.defs.qspec import parse_select
    kind = key[0]
    if kind == 'field':
        # Primeiro tenta getattr direto
        val = getattr(row, key[1], None)
        if val is not None:
            return val
        # Se falhou, tenta encontrar a entrada do select com esse field
        # e usar o nome (alias) da entrada
        if entries:
            for e in entries:
                if e.field == key[1]:
                    # Usar o alias da entrada
                    return getattr(row, e.name, None)
        return None
    if kind == 'expr' and key[1] == 'coalesce':
        for f in key[2]:
            v = getattr(row, f, None)
            if v is not None:
                return v
        return None
    raise ValueError(f"expressão '{key[1]}' sem avaliador em qrun")


def _skey_for(okeys, entries=None):
    # Convenção do motor (igual a core/query._cmp_value): None vem antes no
    # asc (raiz com pai_id null abre o grupo), por último no desc.
    def _skey(r):
        out = []
        for key in okeys:
            desc = key[-1]
            v = _eval_key(r, key, entries=entries)
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

        _skey = _skey_for(okeys, entries)

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


def _sort_rows(rows, order, model, entries=None):
    """Ordenação final incluindo computados (grupo/index) — estável sobre o SQL."""
    from ajsystem.defs.qspec import normalize_order
    okeys = normalize_order(order)
    if not okeys:
        return rows
    cols = set(getattr(model, '__table__', None).columns.keys()) if getattr(model, '__table__', None) is not None else set()
    # Build sets of names from select entries
    entry_names = set()  # aliases (e.name)
    entry_fields = set()  # field paths (e.field)
    if entries:
        for e in entries:
            entry_names.add(e.name)
            entry_fields.add(e.field or e.name)
    for key in okeys:
        fields = [key[1]] if key[0] == 'field' else list(key[2])
        for f in fields:
            # Check if field exists in model columns, or as row attribute, or as select entry name, or as select entry field
            if (f not in cols 
                and not hasattr(rows[0] if rows else object(), f) 
                and f not in entry_names 
                and f not in entry_fields):
                raise ValueError(f"query.order: campo '{f}' não existe (nem coluna, nem computado, nem entrada do select)")
    return sorted(rows, key=_skey_for(okeys, entries))


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


def run_query(model, spec, entity_cfg=None, extra_where=None,
              extra_conditions=None):
    """Executa QuerySpec sobre model. Devolve list de instâncias (+ attrs over).

    `extra_where` usa a gramática declarativa dos filtros; `extra_conditions`
    recebe condições SQLAlchemy já compiladas (ex.: `filter.fixed`) e as
    aplica antes dos OVERs, para que janelas e `calc` enxerguem o recorte.
    """
    qs = parse_query(spec)
    from sqlalchemy import func as _fn
    extra_conditions = [c for c in (extra_conditions or []) if c is not None]
    query = model.query

    # Normalizar order: índices numéricos (1-based) mapeiam para o nome do
    # campo na mesma posição do select. Ex: [1, 2] -> ['conta.nome', 'vencimento'].
    if qs.order:
        _normalized_order = []
        for _item in qs.order:
            _idx = None
            if isinstance(_item, int):
                _idx = _item - 1
            elif isinstance(_item, str) and _item.isdigit():
                _idx = int(_item) - 1
            if _idx is not None and qs.entries and 0 <= _idx < len(qs.entries):
                _normalized_order.append(qs.entries[_idx].field or qs.entries[_idx].name)
            else:
                _normalized_order.append(_item)
        qs.order = _normalized_order

    # Process join specification
    if qs.join is not None:
        joins = _normalize_joins(qs.join)
        for join_spec in joins:
            query = _apply_join(query, model, join_spec, entity_cfg)

    # Join automático para campos do select que são caminhos pontilhados
    # através de relationships (ex.: 'conta.nome' em Previsao).
    for _e in (qs.entries or []):
        if _e.field and '.' in _e.field:
            query, _tmp_model, _ = _resolve_join_path_for_query(query, model, _e.field)

    query = apply_where(query, model, qs.where, entity_cfg)
    query = apply_where(query, model, extra_where, entity_cfg)
    if extra_conditions:
        query = query.filter(*extra_conditions)

    # Construir lista de colunas para with_entities
    # Campos com caminho pontilhado (ex.: 'conta.nome') precisam ser selecionados
    # explicitamente com o alias correto (o nome da entrada no select).
    select_cols = []
    select_names = []
    for e in qs.entries or []:
        if e.field and '.' in e.field:
            _m, _fname = _resolve_path_model(model, e.field)
            col = getattr(_m, _fname, None)
            if col is not None:
                select_cols.append(col.label(e.name))
                select_names.append(e.name)
        else:
            col = getattr(model, e.field or e.name, None)
            if col is not None:
                select_cols.append(col)
                select_names.append(e.name)

    # Se há campos com caminho pontilhado, usar with_entities para selecionar
    # apenas as colunas necessárias (incluindo as de tabelas joined).
    # Se não há campos com caminho pontilhado, usar query.all() que seleciona
    # todas as colunas do model principal.
    has_dotted = any(e.field and '.' in e.field for e in qs.entries or [])

    # GROUP BY + aggs fora de over -> agregação SQL (reduz linhas)
    group_fields = list(qs.groups or [])
    _row_names = []
    _sql_cols = []
    for g in group_fields:
        _field = g
        if qs.entries and not getattr(model, g, None):
            for _e in qs.entries:
                if _e.name == g and _e.field:
                    _field = _e.field
                    break
        if '.' in _field:
            query, _tmp_model, _field = _resolve_join_path_for_query(query, model, _field)
            col = getattr(_tmp_model, _field, None)
        else:
            col = getattr(model, _field, None)
        if col is not None:
            _row_names.append(g)
            _sql_cols.append(col)
    group_cols = _sql_cols

    agg_entries = [e for e in (qs.entries or []) if e.agg and e.over is None]
    if group_cols or agg_entries:
        cols, labels = [], []
        for col in group_cols:
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
            q = query.with_entities(*cols)
            if group_cols:
                q = q.group_by(*group_cols)
            ocols, q = _order_cols(q, model, qs.order)
            if ocols:
                q = q.order_by(*ocols)
            if qs.limit:
                q = q.limit(int(qs.limit))

            class _Row:
                pass
            rows = []
            for tup in q.all():
                vals = list(tup)
                r = _Row()
                for k, v in zip(_row_names + labels, vals):
                    setattr(r, k, v)
                setattr(r, 'id', getattr(r, 'id', None))
                rows.append(r)
            return rows

    # Caminho sem GROUP BY: usar with_entities se há campos com caminho pontilhado,
    # caso contrário usar query.all() que seleciona todas as colunas do model.
    if has_dotted and select_cols:
        q = query.with_entities(*select_cols)
        ocols, q = _order_cols(q, model, qs.order)
        if ocols:
            q = q.order_by(*ocols)
        if qs.limit:
            q = q.limit(int(qs.limit))

        class _Row:
            pass
        rows = []
        for tup in q.all():
            vals = list(tup)
            r = _Row()
            for k, v in zip(select_names, vals):
                setattr(r, k, v)
            setattr(r, 'id', getattr(r, 'id', None))
            rows.append(r)
    else:
        ocols, query = _order_cols(query, model, qs.order)
        if ocols:
            query = query.order_by(*ocols)
        if qs.limit:
            query = query.limit(int(qs.limit))
        rows = list(query.all())

    # If joins were applied, eagerly load joined fields onto instances
    if qs.join is not None:
        joins = _normalize_joins(qs.join)
        for join_spec in joins:
            relation = join_spec.get('relation')
            if not relation:
                continue
            # Eagerly load the relationship for each row
            for row in rows:
                rel_obj = getattr(row, relation, None)
                if rel_obj is not None:
                    # Set joined fields as attributes on the row
                    for attr in dir(rel_obj):
                        if not attr.startswith('_') and attr not in row.__dict__:
                            try:
                                val = getattr(rel_obj, attr)
                                if not callable(val):
                                    setattr(row, attr, val)
                            except Exception:
                                pass

    _validate_calc(qs.entries or [], model)
    rows = _compute_over(rows, qs.entries or [], model)
    rows = _compute_calc(rows, qs.entries or [], model)
    rows = _sort_rows(rows, qs.order, model, qs.entries)
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


def _validate_calc(entries, model):
    """calc referencia coluna do model ou entrada over/agg — nunca outro calc
    (a ordem do select é de exibição; avaliação é over -> calc, sem cadeia)."""
    import re as _re
    cols = set(getattr(model, '__table__', None).columns.keys()) if getattr(model, '__table__', None) is not None else set()
    calcs = {e.name for e in entries or [] if e.calc}
    known = cols | {e.name for e in entries or []}
    for e in entries or []:
        if not e.calc:
            continue
        for nm in set(_re.findall(r'{\??(\w+)', e.calc)):
            if nm not in known:
                raise ValueError(f"select '{e.name}': calc referencia campo desconhecido '{nm}'")
            if nm in calcs:
                raise ValueError(f"select '{e.name}': calc não pode referenciar outro calc ('{nm}')")


def _eval_key(row, key, entries=None):
    """Avalia 1 chave normalizada ('field'| 'expr') sobre a linha."""
    from ajsystem.defs.qspec import parse_select
    kind = key[0]
    if kind == 'field':
        # Primeiro tenta getattr direto
        val = getattr(row, key[1], None)
        if val is not None:
            return val
        # Se falhou, tenta encontrar a entrada do select com esse field
        # e usar o nome (alias) da entrada
        if entries:
            for e in entries:
                if e.field == key[1]:
                    # Usar o alias da entrada
                    return getattr(row, e.name, None)
        return None
    if kind == 'expr' and key[1] == 'coalesce':
        for f in key[2]:
            v = getattr(row, f, None)
            if v is not None:
                return v
        return None
    raise ValueError(f"expressão '{key[1]}' sem avaliador em qrun")


def _skey_for(okeys, entries=None):
    # Convenção do motor (igual a core/query._cmp_value): None vem antes no
    # asc (raiz com pai_id null abre o grupo), por último no desc.
    def _skey(r):
        out = []
        for key in okeys:
            desc = key[-1]
            v = _eval_key(r, key, entries=entries)
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

        _skey = _skey_for(okeys, entries)

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


def _sort_rows(rows, order, model, entries=None):
    """Ordenação final incluindo computados (grupo/index) — estável sobre o SQL."""
    from ajsystem.defs.qspec import normalize_order
    okeys = normalize_order(order)
    if not okeys:
        return rows
    cols = set(getattr(model, '__table__', None).columns.keys()) if getattr(model, '__table__', None) is not None else set()
    # Build sets of names from select entries
    entry_names = set()  # aliases (e.name)
    entry_fields = set()  # field paths (e.field)
    if entries:
        for e in entries:
            entry_names.add(e.name)
            entry_fields.add(e.field or e.name)
    for key in okeys:
        fields = [key[1]] if key[0] == 'field' else list(key[2])
        for f in fields:
            # Check if field exists in model columns, or as row attribute, or as select entry name, or as select entry field
            if (f not in cols 
                and not hasattr(rows[0] if rows else object(), f) 
                and f not in entry_names 
                and f not in entry_fields):
                raise ValueError(f"query.order: campo '{f}' não existe (nem coluna, nem computado, nem entrada do select)")
    return sorted(rows, key=_skey_for(okeys, entries))


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


def run_query(model, spec, entity_cfg=None, extra_where=None,
              extra_conditions=None):
    """Executa QuerySpec sobre model. Devolve list de instâncias (+ attrs over).

    `extra_where` usa a gramática declarativa dos filtros; `extra_conditions`
    recebe condições SQLAlchemy já compiladas (ex.: `filter.fixed`) e as
    aplica antes dos OVERs, para que janelas e `calc` enxerguem o recorte.
    """
    qs = parse_query(spec)
    from sqlalchemy import func as _fn
    extra_conditions = [c for c in (extra_conditions or []) if c is not None]
    query = model.query

    # Inicializar variáveis para evitar UnboundLocalError
    select_cols = []
    select_names = []
    cols = []

    # Normalizar order: índices numéricos (1-based) mapeiam para o nome do
    # campo na mesma posição do select. Ex: [1, 2] -> ['conta.nome', 'vencimento'].
    if qs.order:
        _normalized_order = []
        for _item in qs.order:
            _idx = None
            if isinstance(_item, int):
                _idx = _item - 1
            elif isinstance(_item, str) and _item.isdigit():
                _idx = int(_item) - 1
            if _idx is not None and qs.entries and 0 <= _idx < len(qs.entries):
                _normalized_order.append(qs.entries[_idx].field or qs.entries[_idx].name)
            else:
                _normalized_order.append(_item)
        qs.order = _normalized_order

    # Process join specification
    if qs.join is not None:
        joins = _normalize_joins(qs.join)
        for join_spec in joins:
            query = _apply_join(query, model, join_spec, entity_cfg)

    # Join automático para campos do select que são caminhos pontilhados
    # através de relationships (ex.: 'conta.nome' em Previsao).
    for _e in (qs.entries or []):
        if _e.field and '.' in _e.field:
            query, _tmp_model, _ = _resolve_join_path_for_query(query, model, _e.field)

    query = apply_where(query, model, qs.where, entity_cfg)
    query = apply_where(query, model, extra_where, entity_cfg)
    if extra_conditions:
        query = query.filter(*extra_conditions)

    # Coletar colunas do select para with_entities
    # Campos com caminho pontilhado (ex.: 'conta.nome') precisam ser selecionados
    # explicitamente com o alias correto (o nome da entrada no select).
    select_cols = []
    select_names = []
    for e in qs.entries or []:
        if e.field and '.' in e.field:
            _m, _fname = _resolve_path_model(model, e.field)
            col = getattr(_m, _fname, None)
            if col is not None:
                cols.append(col.label(e.name))
                select_cols.append(col.label(e.name))
                select_names.append(e.name)
        else:
            col = getattr(model, e.field or e.name, None)
            if col is not None:
                cols.append(col)
                select_cols.append(col)
                select_names.append(e.name)

    # Se há campos com caminho pontilhado, usar with_entities para selecionar
    # apenas as colunas necessárias (incluindo as de tabelas joined)
    has_dotted = any(e.field and '.' in e.field for e in qs.entries or [])

    # GROUP BY + aggs fora de over -> agregação SQL (reduz linhas)
    group_fields = list(qs.groups or [])
    _row_names = []
    _sql_cols = []
    for g in group_fields:
        _field = g
        if qs.entries and not getattr(model, g, None):
            for _e in qs.entries:
                if _e.name == g and _e.field:
                    _field = _e.field
                    break
        if '.' in _field:
            query, _tmp_model, _field = _resolve_join_path_for_query(query, model, _field)
            col = getattr(_tmp_model, _field, None)
        else:
            col = getattr(model, _field, None)
        if col is not None:
            _row_names.append(g)
            _sql_cols.append(col)
    group_cols = _sql_cols

    agg_entries = [e for e in (qs.entries or []) if e.agg and e.over is None]
    if group_cols or agg_entries:
        cols, labels = [], []
        for col in group_cols:
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
            q = query.with_entities(*cols)
            if group_cols:
                q = q.group_by(*group_cols)
            ocols, q = _order_cols(q, model, qs.order)
            if ocols:
                q = q.order_by(*ocols)
            if qs.limit:
                q = q.limit(int(qs.limit))

            class _Row:
                pass
            rows = []
            for tup in q.all():
                vals = list(tup)
                r = _Row()
                for k, v in zip(_row_names + labels, vals):
                    setattr(r, k, v)
                setattr(r, 'id', getattr(r, 'id', None))
                rows.append(r)
            return rows

    # Caminho sem GROUP BY: usar with_entities se há campos com caminho pontilhado
    if has_dotted and select_cols:
        q = query.with_entities(*select_cols)
        ocols, q = _order_cols(q, model, qs.order)
        if ocols:
            q = q.order_by(*ocols)
        if qs.limit:
            q = q.limit(int(qs.limit))

        class _Row:
            pass
        rows = []
        for tup in q.all():
            vals = list(tup)
            r = _Row()
            for k, v in zip(select_names, vals):
                setattr(r, k, v)
            setattr(r, 'id', getattr(r, 'id', None))
            rows.append(r)
    else:
        ocols, query = _order_cols(query, model, qs.order)
        if ocols:
            query = query.order_by(*ocols)
        if qs.limit:
            query = query.limit(int(qs.limit))
        rows = list(query.all())

    # If joins were applied, eagerly load joined fields onto instances
    if qs.join is not None:
        joins = _normalize_joins(qs.join)
        for join_spec in joins:
            relation = join_spec.get('relation')
            if not relation:
                continue
            for row in rows:
                rel_obj = getattr(row, relation, None)
                if rel_obj is not None:
                    for attr in dir(rel_obj):
                        if not attr.startswith('_') and attr not in row.__dict__:
                            try:
                                val = getattr(rel_obj, attr)
                                if not callable(val):
                                    setattr(row, attr, val)
                            except Exception:
                                pass

    _validate_calc(qs.entries or [], model)
    rows = _compute_over(rows, qs.entries or [], model)
    rows = _compute_calc(rows, qs.entries or [])
    rows = _sort_rows(rows, qs.order, model, qs.entries)
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


