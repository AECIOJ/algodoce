"""Orquestrador `do_list` — request → response para listagens.

Reescrito do zero observando `core/old/do_list.py`. Lê `Page`/`Schema` (dicts
declarativos) do módulo de rota e resolve os campos via `defs.data`
(merge `Entity(model)` + `Schema`). Mantém os contratos de render de
`pages/list.html`.
"""
import importlib

from flask import Blueprint, render_template, request, url_for

from app.ajsystem.defs.data import (
    _auto_label, build_field, page_list_cfg, resolve_entity_fields, module_page,
    resolve_max_width,
)
from app.ajsystem.core.list import (
    List, build_filter_config, build_field_context, resolve_column_configs,
    fields_to_columns, _resolve_model,
)
from app.ajsystem.core.filters import resolve_filters

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
    bp_name = _module_blueprint(mod).name if _module_blueprint(mod) else None
    model = _resolve_model(entity_name)
    merged = resolve_entity_fields(schema, model, entity_name)
    fields = resolve_column_configs(merged, lista.get('columns', lista.get('fields', entity_name)), principal=merged)
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


def _module_blueprint(mod):
    for name in dir(mod):
        obj = getattr(mod, name, None)
        if isinstance(obj, Blueprint):
            return obj
    return None


def _resolve_endpoint(lista, key, bp_name):
    if key in lista:
        return lista.get(key)
    return f"{bp_name}.form" if bp_name else None


def do_list(entity_name: str, module_name: str, data=None, **extra):
    mod = importlib.import_module(module_name)
    schema = getattr(mod, 'Schema', None) or {}
    page = module_page(mod)
    tabs, active_tab = build_tabs(page)
    lista = page_list_cfg(page)
    bp_name = _module_blueprint(mod).name if _module_blueprint(mod) else None

    model = _resolve_model(entity_name)
    merged = resolve_entity_fields(schema, model, entity_name)

    fields = resolve_column_configs(merged, lista.get('columns', lista.get('fields', entity_name)), principal=merged)
    fields_all = list(fields)
    fields = [f for f in fields if f.pos_list != 0]

    line_fields = [f for f in fields if f.pos_list == 1]
    cardonly_fields = [f for f in fields if f.pos_list == 2]
    if not line_fields:
        line_fields, cardonly_fields = fields, []

    card_fields = None
    card_configs = resolve_column_configs(merged, lista.get('card', []), principal=merged)
    card_fields = card_configs or None

    all_fields = line_fields + cardonly_fields + (card_fields or [])
    fields_master = list(range(1, len(line_fields) + 1))

    linha_names = lista.get('linha') or []
    linha_names = [n.split('.', 1)[-1] for n in linha_names]
    linha_indices = [i for i, f in enumerate(line_fields) if f.name in linha_names] if linha_names else None

    edit_endpoint = _resolve_endpoint(lista, 'edit_endpoint', bp_name)

    from app.ajsystem.defs.data import resolve_lookup
    for f in (line_fields + cardonly_fields + (card_fields or [])):
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
    from app.ajsystem.core import do_report as _drp
    rid = request.args.get('_r')
    _print_field = _drp._print_field_of(rid) if rid else None
    _fargs = {k: v for k, v in request.args.items(multi=True) if k != _print_field}
    initial_filters, active = resolve_filters(filter_config, _fargs)

    from app.ajsystem.core.filters import fixed_filters as _fixed_filters
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

    from app.ajsystem.core.filters import apply_filters
    for field, filter_value in active.items():
        ftype = filter_config.get(field, {}).get('type', 'text')
        if ftype == 'date' and isinstance(filter_value, dict):
            from app.ajsystem.core.filters import filtrar_vencimento_query
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
        from app.ajsystem.core import do_report as _dr
        auto_report = _dr._consume_pending_print(rid)

    title = lista.get('title') or _auto_label(entity_name)
    new_endpoint = _resolve_endpoint(lista, 'new_endpoint', bp_name)
    new_url = url_for(new_endpoint) if new_endpoint else None
    new_label = 'Incluir ' + _auto_label(entity_name)

    template = (lista.get('template') or "pages/list.html")

    return render_template(
        template,
        entity_name=entity_name,
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
