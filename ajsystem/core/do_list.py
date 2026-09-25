"""Orquestrador `do_list` — request → response para listagens.

Reescrito do zero observando `core/old/do_list.py`. Lê `Page`/`Schema` (dicts
declarativos) do módulo de rota e resolve os campos via `defs.data`
(merge `Entity(model)` + `Schema`). Mantém os contratos de render de
`pages/list.html`.
"""
import importlib

from flask import render_template, request, url_for

from ajsystem.defs.data import (
    _auto_label, build_field, page_list_cfg, resolve_entity_fields, module_page,
    resolve_max_width,
)
from ajsystem.core.list import (
    List, build_filter_config, build_field_context, resolve_column_configs,
    fields_to_columns, _resolve_model,
)
from ajsystem.core.filters import resolve_filters
from ajsystem.core.utils import module_blueprint

TAB_TYPES = ('List', 'Filter', 'Report', 'Custom')


def _default_type(key):
    norm = (key or '').strip().lower()
    if norm == 'dados':
        return 'List'
    if norm in ('filtros', 'filtrar'):
        return 'Filter'
    if norm == 'relatorios' or norm == 'relatório' or norm == 'relatórios' or norm == 'reports' or norm == 'report':
        return 'Report'
    return 'Custom'


def _total_ch(fields, edit_endpoint) -> str:
    """`ch` da soma das colunas + ações — cálculo compartilhado pela listagem."""
    tot = sum(col['width'] for col in fields_to_columns(fields))
    tot += 16 if edit_endpoint else 0
    tot += 3
    return f'{tot}ch'


def _list_default_max_width(lista: List) -> str:
    """Largura padrão de lista sem `max_width`: soma das colunas + ações.

    Espelha o cálculo que antes vivia em `pages/list.html` (`tot_ch`).
    """
    return _total_ch(lista.master_fields, lista.edit_endpoint)


def list_max_width(entity_name: str, module_name: str) -> str:
    """Largura final que a listagem do módulo resolve (max_width explícito ou
    padrão `tot_ch`). O container do meio do form segue essa largura quando
    `form.max_width` não é declarado (consome em `core.do_form`)."""
    mod = importlib.import_module(module_name)
    schema = getattr(mod, 'Schema', None) or {}
    page = module_page(mod)
    lista = page_list_cfg(page)
    bp_name = module_blueprint(mod).name if module_blueprint(mod) else None
    model = _resolve_model(entity_name)
    merged = resolve_entity_fields(schema, model, entity_name)
    fields = resolve_column_configs(merged, lista.get('columns', lista.get('fields', entity_name)), principal=merged)
    if not any(f._pos_managed for f in fields):
        line_fields = list(fields)
    else:
        fields = [f for f in fields if f.pos_list != 0]
        line_fields = [f for f in fields if f.pos_list == 1] or fields
    edit_endpoint = _resolve_endpoint(lista, 'edit_endpoint', bp_name)
    return resolve_max_width(lista.get('max_width')) or _total_ch(line_fields, edit_endpoint)


def build_tabs(page: dict):
    """Reconstrói a lista de abas + aba ativa a partir do `Page` dict."""
    tabs = []
    props = (page or {}).get('props') or {}
    tab_specs = props.get('tabs')
    list_cfg = props.get('list')
    if not tab_specs:
        tab_specs = {'Dados': {'type': 'List'}}
    for key, cfg in (tab_specs or {}).items():
        cfg = dict(cfg or {})
        ttype = cfg.pop('type', None) or _default_type(key)
        if ttype == 'List' and list_cfg:
            cfg.update(list_cfg)
        tabs.append({
            'id': key,
            'type': ttype,
            'template': cfg.pop('template', None),
            'config': cfg,
        })
    for t in tabs:
        if t['type'] not in TAB_TYPES:
            raise ValueError(f"Page: tipo inválido '{t['type']}' na aba '{t['id']}'")
    if not any(t['type'] == 'Filter' for t in tabs):
        tabs.append({'id': 'Filtros', 'type': 'Filter', 'template': None, 'config': {}})
    return tabs, (tabs[0]['id'] if tabs else '')


def _resolve_endpoint(lista, key, bp_name):
    if key in lista:
        return lista.get(key)
    return f"{bp_name}.form" if bp_name else None


def _inversion_parent_rel_key(lista, merged, child_model):
    """Nome da relação filho→pai na inversão (`master`), ou `None`.

    Ex.: no `pagar` invertido (master `Previsao`, entidade `Transacao`), a
    `Previsao` alcança o pai pela relação `transacao`.
    """
    if not merged:
        return None
    from ajsystem.core.list import _resolve_model
    child_key = next((k for k in merged
                      if k.lower() == child_model.__name__.lower()), None)
    parent_name = next((k for k in merged if k != child_key), None)
    parent_model = _resolve_model(parent_name) if parent_name else None
    if parent_model is None:
        return None
    mapper = getattr(child_model, '__mapper__', None)
    if mapper is None:
        return None
    for rel_key, rel_prop in mapper.relationships.items():
        if rel_prop.mapper.class_ is parent_model:
            return rel_key
    return None


def _inversion_parent_rel(lista, merged, child_model):
    """Relação filho→pai na inversão (`master`), ou `None`.

    Ex.: no `pagar` invertido (master `Previsao`, entidade `Transacao`), a
    `Previsao` alcança o pai pela relação `previsao.transacao`.
    """
    key = _inversion_parent_rel_key(lista, merged, child_model)
    return getattr(child_model, key) if key else None


def _inversion_order_attr(lista, merged, child_model, name):
    """Atributo de ordenação/filtro na inversão (`master`).

    `name` pode ser coluna do pai (ex.: no `pagar` invertido, `data`/`tipo`
    são da `Transacao`, não da `Previsao`): então devolve a coluna do pai
    (`Transacao.data`). A query-fonte (`_base_query`) já faz o `JOIN` com o pai
    nesse modo, então a coluna é usável direto em `order_by`/`filter`. Coluna
    do filho → devolve a coluna do filho; inexistente → `None`."""
    direct = getattr(child_model, name, None)
    if direct is not None:
        return direct
    from ajsystem.core.list import _resolve_model
    child_key = next((k for k in merged
                      if k.lower() == child_model.__name__.lower()), None)
    parent_name = next((k for k in merged if k != child_key), None)
    parent_model = _resolve_model(parent_name) if parent_name else None
    return getattr(parent_model, name, None) if parent_model is not None else None


def _inversion_order_precedence(child_model, principal_model, name):
    """Prioridade de um campo na ordenação da inversão (`master`):
    0 = campo da entidade `master` (filho); 1 = campo do pai; 2 = outro.

    Particionamento estável: dentro de cada grupo preserva-se a ordem
    declarada no `order`."""
    if getattr(child_model, name, None) is not None:
        return 0
    if getattr(principal_model, name, None) is not None:
        return 1
    return 2


def _card_layer(card_spec, merged, row_entity):
    """Prop `card` do list → camada de config para `resolve_entity_fields`.

    A camada entra entre Entity e Schema (`{**Entity, **card, **Schema}`): marca
    `pos_list: 2` (card) nos campos citados; o Schema por cima vence sempre.
    Formatos aceitos (mesma família de `fields`/`columns`):
      - `'Entity'`            → todos os campos da entidade
      - `['f1', 'Ent.f2']`    → nomes simples (entidade das linhas) ou com prefixo
      - `{'Entity': ['f1']}`  → agrupado por entidade
    Retorna `{entidade: {campo: cfg}}` (vazio se a prop não existir).
    """
    if not card_spec:
        return {}
    out = {}

    def _push(entity, name):
        if name:
            out.setdefault(entity, {})[name] = {'pos_list': 2}

    if isinstance(card_spec, str):
        for name in merged.get(card_spec, {}) or {}:
            _push(card_spec, name)
    elif isinstance(card_spec, list):
        for item in card_spec:
            if not isinstance(item, str):
                continue
            if '.' in item:
                ent, name = item.split('.', 1)
                _push(ent, name)
            else:
                _push(row_entity, item)
    elif isinstance(card_spec, dict):
        for ent, names in card_spec.items():
            if isinstance(names, list):
                for name in names:
                    _push(ent, name)
            else:
                _push(row_entity, ent)
    return {k: v for k, v in out.items() if v}


def do_list(entity_name: str, module_name: str, data=None, **extra):
    """Entrada da listagem — roteia para `do_list_normal` (sem inversão) ou
    `do_list_master` (inversão de relacionamento, prop `master`)."""
    mod = importlib.import_module(module_name)
    page = module_page(mod)
    lista = page_list_cfg(page)
    if (lista or {}).get('master'):
        return do_list_master(entity_name, module_name, data=data, **extra)
    return do_list_normal(entity_name, module_name, data=data, **extra)


def do_list_normal(entity_name: str, module_name: str, data=None, **extra):
    """Listagem comum — fluxo original intacto (sem inversão `master`)."""
    mod = importlib.import_module(module_name)
    schema = getattr(mod, 'Schema', None) or {}
    page = module_page(mod)
    tabs, active_tab = build_tabs(page)
    lista = page_list_cfg(page)
    bp_name = module_blueprint(mod).name if module_blueprint(mod) else None

    model = _resolve_model(entity_name)
    merged = resolve_entity_fields(schema, model, entity_name)
    card_layer = _card_layer(lista.get('card'), {entity_name: merged}, entity_name)
    if card_layer:
        merged = resolve_entity_fields(schema, model, entity_name, card_layer)

    fields = resolve_column_configs(merged, lista.get('columns', lista.get('fields', entity_name)), principal=merged)
    fields_all = list(fields)
    if not any(f._pos_managed for f in fields):
        # lista explícita de campos → autoritativa (pos_list não filtra)
        line_fields = list(fields)
        cardonly_fields = []
    else:
        fields = [f for f in fields if f.pos_list != 0]
        line_fields = [f for f in fields if f.pos_list == 1]
        cardonly_fields = [f for f in fields if f.pos_list == 2]
        if not line_fields:
            line_fields, cardonly_fields = fields, []

    card_fields = None

    all_fields = line_fields + cardonly_fields
    stored_cols = {c.name for c in model.__table__.columns}
    for f in all_fields:
        f.stored = f.name in stored_cols
    fields_master = list(range(1, len(line_fields) + 1))

    linha_names = lista.get('linha') or []
    linha_names = [n.split('.', 1)[-1] for n in linha_names]
    linha_indices = [i for i, f in enumerate(line_fields) if f.name in linha_names] if linha_names else None

    edit_endpoint = _resolve_endpoint(lista, 'edit_endpoint', bp_name)

    from ajsystem.defs.data import resolve_lookup
    for f in line_fields + cardonly_fields:
        resolved = resolve_lookup(f, model)
        if resolved is not None:
            f.lookup = resolved

    list_obj = List(
        fields=all_fields,
        fields_master=fields_master,
        edit_endpoint=edit_endpoint,
        edit_id_field=lista.get('edit_id_field', 'id'),
        template=lista.get('template'),
        linha=linha_indices,
        card_idx=(list(range(len(line_fields) + 1, len(all_fields) + 1))
                  if len(all_fields) > len(line_fields) else None),
        buttons=lista.get('buttons'),
    )
    buttons = list_obj.resolve_buttons(bp_name)

    detail_fields = None
    detail_data = None
    if 'detail' in lista:
        _dspec = lista['detail']
        if isinstance(_dspec, dict):
            _dfields, detail_data = _dspec.get('fields', []), _dspec.get('data')
        else:
            _dfields, detail_data = _dspec, entity_name.lower() + '_items'
        if detail_data:
            _rel = getattr(model, detail_data, None)
            try:
                _child = _rel.property.mapper.class_ if _rel is not None else None
            except Exception:
                _child = None
            if _child is not None:
                _cmerged = resolve_entity_fields(schema, _child, _child.__name__)
            else:
                _cmerged = merged
            detail_fields = resolve_column_configs(_cmerged, _dfields, principal=_cmerged)
        else:
            detail_fields = resolve_column_configs(merged, _dfields, principal=merged)
        list_obj.detail_data = detail_data

    filter_config = build_filter_config(list_obj.fields)

    # Campo de impressão com escolha ativo (marcador `_r`): o parâmetro que o
    # relatório injetou na URL não deve virar filtro da listagem, senão o filtro
    # de impressão persistiria na lista ao "Voltar". Resolve-se a listagem sem
    # esse campo.
    from ajsystem.core import do_report as _drp
    rid = request.args.get('_r')
    _print_field = _drp._print_field_of(rid) if rid else None
    _fargs = {k: v for k, v in request.args.items(multi=True) if k != _print_field}
    initial_filters, active = resolve_filters(filter_config, _fargs)

    from ajsystem.core.filters import fixed_filters as _fixed_filters
    _fixed = _fixed_filters(fields_all, model)

    def _base_query():
        q = model.query
        for _mf, _v in _fixed:
            q = q.filter(_mf == _v)
        return q

    if data is None:
        ordering = lista.get('order', []) or lista.get('ordering', [])
        if isinstance(ordering, str):
            ordering = [ordering]
        if ordering:
            data = _base_query().order_by(*[getattr(model, c) for c in ordering]).all()
        else:
            data = _base_query().all()

    calc_field = next((f for f in line_fields if callable(getattr(f, 'calc', None))), None)
    if calc_field and data:
        data = sorted(data, key=calc_field.calc)

    from ajsystem.core.filters import apply_filters
    for field, filter_value in active.items():
        ftype = filter_config.get(field, {}).get('type', 'text')
        if ftype == 'date' and isinstance(filter_value, dict):
            from ajsystem.core.filters import filtrar_vencimento_query
            query = _base_query()
            query = filtrar_vencimento_query(query, getattr(model, field),
                                             filter_value.get('preset'),
                                             filter_value.get('from'))
            ord_fb = lista.get('order', ['id']) or lista.get('ordering', ['id'])
            if isinstance(ord_fb, str):
                ord_fb = [ord_fb]
            data = query.order_by(*[getattr(model, c) for c in ord_fb]).all()
            continue
        model_field = getattr(model, field, None)
        if model_field is None:
            continue
        query = _base_query()
        query = apply_filters(query, model_field, ftype, filter_value)
        ordering = lista.get('order', ['id']) or lista.get('ordering', ['id'])
        if isinstance(ordering, str):
            ordering = [ordering]
        data = query.order_by(*[getattr(model, c) for c in ordering]).all()

    ctx = build_field_context(list_obj.fields)

    # Impressão com escolha (render interno): se a request traz o marcador
    # `_r` de um modal de `filter_select`, gera o fragmento do PDF aqui e o
    # injeta automaticamente no load (reportRender), sem rota nova. O botão de
    # impressão continua sempre devolvendo o modal, permitindo reimprimir com
    # outro critério.
    auto_report = None
    if rid:
        from ajsystem.core import do_report as _dr
        auto_report = _dr._consume_pending_print(rid)

    title = lista.get('title') or _auto_label(entity_name)
    new_endpoint = _resolve_endpoint(lista, 'new_endpoint', bp_name)
    new_url = url_for(new_endpoint) if new_endpoint else None
    new_label = 'Incluir ' + _auto_label(entity_name)

    template = (lista.get('template') or "pages/list.html")

    return render_template(
        template,
        entity_name=entity_name,
        list_page=True,
        TABS=tabs,
        active_tab=active_tab,
        LIST=list_obj,
        data=data,
        active_filters=active,
        initial_filters=initial_filters,
        FILTERS=filter_config,
        ctx=ctx,
        title=title,
        new_url=new_url,
        new_label=new_label,
        max_width=(resolve_max_width(lista.get('max_width'))
                  or _list_default_max_width(list_obj)),
        detail_fields=detail_fields,
        detail_data=detail_data,
        card_fields=card_fields,
        cardonly_fields=cardonly_fields,
        buttons=buttons,
        auto_report=auto_report,
        **extra,
    )


def do_list_master(entity_name: str, module_name: str, data=None, **extra):
    """Listagem invertida (`master`) — fluxo próprio, separado da listagem comum.

    As linhas passam a ser os registros do filho (`master`); a entidade da
    rota (`entity_name`) é o pai alcançado por relação. Regras da inversão:
      - colunas: começam pelos campos da entidade `master` (pos_list), seguidas
        dos campos do pai;
      - ordenação: campos da entidade `master` primeiro, depois os do pai
        (requer `JOIN` com o pai para alcançar as colunas dele);
      - filtros continuam pelos campos em pos_list (resolvendo colunas do pai
        pela relação).
    """
    mod = importlib.import_module(module_name)
    schema = getattr(mod, 'Schema', None) or {}
    page = module_page(mod)
    tabs, active_tab = build_tabs(page)
    lista = page_list_cfg(page)
    bp_name = module_blueprint(mod).name if module_blueprint(mod) else None

    master_name = lista.get('master') or None
    principal_model = _resolve_model(entity_name)
    child_model = _resolve_model(master_name)
    model = child_model
    _merged0 = {
        entity_name: resolve_entity_fields(schema, principal_model, entity_name),
        master_name: resolve_entity_fields(schema, child_model, master_name),
    }
    card_layer = _card_layer(lista.get('card'), _merged0, master_name)
    if card_layer:
        merged = {
            entity_name: resolve_entity_fields(schema, principal_model, entity_name, card_layer),
            master_name: resolve_entity_fields(schema, child_model, master_name, card_layer),
        }
    else:
        merged = _merged0

    spec = lista.get('columns', lista.get('fields', entity_name))

    def _resolve_tagged(entity_key):
        cfgs = resolve_column_configs(merged, entity_key, principal=merged)
        for f in cfgs:
            f._entity = entity_key
        return cfgs

    if isinstance(spec, str) and spec == entity_name:
        # colunas master primeiro: todos os campos da entidade `master`
        # (pos_list), seguidos dos campos do pai.
        fields = _resolve_tagged(master_name) + _resolve_tagged(entity_name)
    else:
        fields = resolve_column_configs(merged, spec, principal=merged)
    fields_all = list(fields)
    if not any(f._pos_managed for f in fields):
        # lista explícita de campos → autoritativa (pos_list não filtra)
        line_fields = list(fields)
        cardonly_fields = []
    else:
        fields = [f for f in fields if f.pos_list != 0]
        line_fields = [f for f in fields if f.pos_list == 1]
        cardonly_fields = [f for f in fields if f.pos_list == 2]
        if not line_fields:
            line_fields, cardonly_fields = fields, []

    card_fields = None

    all_fields = line_fields + cardonly_fields
    stored_cols = {c.name for c in model.__table__.columns}
    for f in all_fields:
        f.stored = f.name in stored_cols
    fields_master = list(range(1, len(line_fields) + 1))

    # Campos do pai (entidade da rota) vivem no registro relacionado da linha:
    # o template resolve o valor por `card_path` (`rel.campo`) e os lookups
    # desses campos também precisam do caminho através da relação (`rel×path`).
    parent_rel = _inversion_parent_rel_key(lista, merged, model)
    for f in line_fields + cardonly_fields:
        if getattr(f, '_entity', None) == entity_name and parent_rel:
            f.card_path = f'{parent_rel}.{f.name}'
            if f.lookup and isinstance(f.lookup, dict) and f.lookup.get('path'):
                f.lookup['path'] = f'{parent_rel}.{f.lookup["path"]}'

    linha_names = lista.get('linha') or []
    linha_names = [n.split('.', 1)[-1] for n in linha_names]
    linha_indices = [i for i, f in enumerate(line_fields) if f.name in linha_names] if linha_names else None

    edit_endpoint = _resolve_endpoint(lista, 'edit_endpoint', bp_name)

    from ajsystem.defs.data import resolve_lookup
    for f in line_fields + cardonly_fields:
        source = principal_model if getattr(f, '_entity', None) == entity_name else model
        resolved = resolve_lookup(f, source)
        if resolved is not None:
            f.lookup = resolved
            if getattr(f, '_entity', None) == entity_name and parent_rel:
                f.lookup['path'] = f'{parent_rel}.{f.lookup["path"]}'

    list_obj = List(
        fields=all_fields,
        fields_master=fields_master,
        edit_endpoint=edit_endpoint,
        edit_id_field=lista.get('edit_id_field', f'{parent_rel}.id' if parent_rel else 'id'),
        template=lista.get('template'),
        linha=linha_indices,
        card_idx=(list(range(len(line_fields) + 1, len(all_fields) + 1))
                  if len(all_fields) > len(line_fields) else None),
        buttons=lista.get('buttons'),
    )
    buttons = list_obj.resolve_buttons(bp_name)

    detail_fields = None
    detail_data = None
    if 'detail' in lista:
        _dspec = lista['detail']
        if isinstance(_dspec, dict):
            _dfields, detail_data = _dspec.get('fields', []), _dspec.get('data')
        else:
            _dfields, detail_data = _dspec, entity_name.lower() + '_items'
        if detail_data:
            _rel = getattr(model, detail_data, None)
            try:
                _child = _rel.property.mapper.class_ if _rel is not None else None
            except Exception:
                _child = None
            if _child is not None:
                _cmerged = resolve_entity_fields(schema, _child, _child.__name__)
            else:
                _cmerged = merged
            detail_fields = resolve_column_configs(_cmerged, _dfields, principal=_cmerged)
        else:
            detail_fields = resolve_column_configs(merged, _dfields, principal=merged)
        list_obj.detail_data = detail_data

    filter_config = build_filter_config(list_obj.fields)

    # Campo de impressão com escolha ativo (marcador `_r`): o parâmetro que o
    # relatório injetou na URL não deve virar filtro da listagem, senão o filtro
    # de impressão persistiria na lista ao "Voltar". Resolve-se a listagem sem
    # esse campo.
    from ajsystem.core import do_report as _drp
    rid = request.args.get('_r')
    _print_field = _drp._print_field_of(rid) if rid else None
    _fargs = {k: v for k, v in request.args.items(multi=True) if k != _print_field}
    initial_filters, active = resolve_filters(filter_config, _fargs)

    from ajsystem.core.filters import fixed_filters as _fixed_filters
    _inversion_resolver = lambda m, n: _inversion_order_attr(lista, merged, m, n)
    _fixed = _fixed_filters(fields_all, model, _inversion_resolver)
    _parent_rel = _inversion_parent_rel(lista, merged, model)

    def _base_query():
        q = model.query
        if _parent_rel is not None:
            q = q.join(_parent_rel)
        for _mf, _v in _fixed:
            q = q.filter(_mf == _v)
        return q

    def _master_ordering():
        order = lista.get('order', []) or lista.get('ordering', [])
        if isinstance(order, str):
            order = [order]
        return sorted(order, key=lambda c: _inversion_order_precedence(model, principal_model, c))

    if data is None:
        ordering = _master_ordering()
        if ordering:
            data = _base_query().order_by(*[_inversion_order_attr(lista, merged, model, c) for c in ordering]).all()
        else:
            data = _base_query().all()

    calc_field = next((f for f in line_fields if callable(getattr(f, 'calc', None))), None)
    if calc_field and data:
        data = sorted(data, key=calc_field.calc)

    from ajsystem.core.filters import apply_filters
    for field, filter_value in active.items():
        ftype = filter_config.get(field, {}).get('type', 'text')
        if ftype == 'date' and isinstance(filter_value, dict):
            from ajsystem.core.filters import filtrar_vencimento_query
            model_field = _inversion_order_attr(lista, merged, model, field)
            if model_field is None:
                continue
            query = _base_query()
            query = filtrar_vencimento_query(query, model_field,
                                             filter_value.get('preset'),
                                             filter_value.get('from'))
            data = query.order_by(*[_inversion_order_attr(lista, merged, model, c)
                                    for c in _master_ordering()]).all()
            continue
        model_field = _inversion_order_attr(lista, merged, model, field)
        if model_field is None:
            continue
        query = _base_query()
        query = apply_filters(query, model_field, ftype, filter_value)
        data = query.order_by(*[_inversion_order_attr(lista, merged, model, c)
                                for c in _master_ordering()]).all()

    ctx = build_field_context(list_obj.fields)

    # Impressão com escolha (render interno): se a request traz o marcador
    # `_r` de um modal de `filter_select`, gera o fragmento do PDF aqui e o
    # injeta automaticamente no load (reportRender), sem rota nova. O botão de
    # impressão continua sempre devolvendo o modal, permitindo reimprimir com
    # outro critério.
    auto_report = None
    if rid:
        from ajsystem.core import do_report as _dr
        auto_report = _dr._consume_pending_print(rid)

    title = lista.get('title') or _auto_label(entity_name)
    new_endpoint = _resolve_endpoint(lista, 'new_endpoint', bp_name)
    new_url = url_for(new_endpoint) if new_endpoint else None
    new_label = 'Incluir ' + _auto_label(entity_name)

    template = (lista.get('template') or "pages/list.html")

    return render_template(
        template,
        entity_name=entity_name,
        list_page=True,
        TABS=tabs,
        active_tab=active_tab,
        LIST=list_obj,
        data=data,
        active_filters=active,
        initial_filters=initial_filters,
        FILTERS=filter_config,
        ctx=ctx,
        title=title,
        new_url=new_url,
        new_label=new_label,
        max_width=(resolve_max_width(lista.get('max_width'))
                  or _list_default_max_width(list_obj)),
        detail_fields=detail_fields,
        detail_data=detail_data,
        card_fields=card_fields,
        cardonly_fields=cardonly_fields,
        buttons=buttons,
        auto_report=auto_report,
        **extra,
    )
