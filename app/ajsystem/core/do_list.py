"""Orquestrador `do_list` — request → response para listagens.

Consome specs puros (`defs.list.List`) e delega a resolução de campos/engine
para `core/list.py`. É o único ponto (além de `core.do_form`) que as
rotas/`core.auto` usam para montar a página de listagem.
"""
import importlib

from flask import Blueprint, render_template, request, url_for

from app.ajsystem.defs.form import _resolve_label
from app.ajsystem.defs.entities import Field, get_field, _derive_fk_ref
from app.ajsystem.core.list import (
    List, build_filter_config, build_field_context,
    _resolve_cols, _resolve_field_names, _resolve_model,
)
from app.ajsystem.core.filters import (
    resolve_filters,
    apply_text_filter,
    apply_number_filter,
    apply_boolean_filter,
    apply_select_filter,
    apply_date_filter,
)


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
    entidades = mod.Entity
    lista = mod.List
    bp_name = _module_blueprint(mod).name if _module_blueprint(mod) else None

    if entity_name not in entidades:
        raise KeyError(f"Entity '{entity_name}' não definida em {module_name}")

    model = _resolve_model(entity_name)

    field_configs = _resolve_cols(lista.get('fields', entity_name), entidades, principal=entidades.get(entity_name))
    fields = [Field(**cfg) for cfg in field_configs]
    fields = [_derive_fk_ref(f, model) for f in fields]
    fields = [f for f in fields if f.in_list != 0]

    line_fields = [f for f in fields if f.in_list == 1]
    cardonly_fields = [f for f in fields if f.in_list == 2]
    if not line_fields:
        line_fields, cardonly_fields = fields, []

    card_fields = None
    card_configs = _resolve_cols(lista.get('card', []), entidades)
    card_fields = [Field(**cfg) for cfg in card_configs] if card_configs else None
    if card_fields:
        card_fields = [_derive_fk_ref(f, model) for f in card_fields]

    all_fields = line_fields + cardonly_fields + (card_fields or [])
    fields_master = list(range(1, len(line_fields) + 1))

    linha_names = _resolve_field_names(lista.get('linha', []))
    linha_indices = [i for i, f in enumerate(line_fields) if f.name in linha_names] if linha_names else None

    edit_endpoint = _resolve_endpoint(lista, 'edit_endpoint', bp_name)

    list_obj = List(
        fields=all_fields,
        fields_master=fields_master,
        edit_endpoint=edit_endpoint,
        edit_id_field=lista.get('edit_id_field', 'id'),
        template=lista.get('template'),
        linha=linha_indices,
        card_idx=(list(range(len(line_fields) + 1, len(all_fields) + 1)) if len(all_fields) > len(line_fields) else None),
    )

    detail_fields = None
    detail_data = None
    if 'detail' in lista:
        det_configs = _resolve_cols(lista['detail'], entidades)
        detail_fields = [Field(**cfg) for cfg in det_configs]
        detail_fields = [_derive_fk_ref(f, model) for f in detail_fields]
        detail_data = entity_name.lower() + '_items'
        list_obj.detail_data = detail_data

    filter_config = build_filter_config(list_obj.fields)
    active = resolve_filters(filter_config, request.args)

    if data is None:
        ordering = lista.get('ordering', [])
        if ordering:
            order_cols = [getattr(model, col) for col in ordering]
            data = model.query.order_by(*order_cols).all()
        else:
            data = model.query.all()

    for field, filter_value in active.items():
        ftype = filter_config.get(field, {}).get('type', 'text')
        if ftype == 'text':
            data = apply_text_filter(data, field, filter_value)
        elif ftype == 'number':
            data = apply_number_filter(data, field, filter_value)
        elif ftype == 'boolean':
            data = apply_boolean_filter(data, field, filter_value)
        elif ftype == 'select':
            field_obj = get_field(list_obj.fields, field)
            options = field_obj.options if field_obj else {}
            filter_path = field_obj.filter_path if field_obj else None
            data = apply_select_filter(data, field, filter_value, options or {}, filter_path)
        elif ftype == 'date':
            data = apply_date_filter(data, field, filter_value)

    ctx = build_field_context(list_obj.master_fields)

    title = lista.get('title', entity_name)
    new_endpoint = _resolve_endpoint(lista, 'new_endpoint', bp_name)
    new_url = url_for(new_endpoint) if new_endpoint else None
    new_label = 'Incluir ' + _resolve_label(mod, entity_name)

    init_filters = {}
    for fname, fcfg in filter_config.items():
        ftype = fcfg.get('type', 'text')
        if ftype == 'text':
            init_filters[fname] = {'mode': 'contains', 'value': ''}
        elif ftype == 'number':
            init_filters[fname] = {'mode': 'igual', 'val1': '', 'val2': ''}
        elif ftype == 'date':
            init_filters[fname] = {'preset': '', 'from': '', 'to': ''}
        elif ftype in ('boolean', 'select'):
            init_filters[fname] = ''
        else:
            init_filters[fname] = ''

    template = lista.get('template') or "pages/list.html"
    return render_template(
        template,
        entity_name=entity_name,
        LIST=list_obj,
        data=data,
        active_filters=active,
        initial_filters=init_filters,
        FILTERS=filter_config,
        ctx=ctx,
        title=title,
        new_url=new_url,
        new_label=new_label,
        detail_fields=detail_fields,
        detail_data=detail_data,
        card_fields=card_fields,
        cardonly_fields=cardonly_fields,
        **extra,
    )
