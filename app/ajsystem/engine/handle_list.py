import importlib
import re
from flask import Blueprint, render_template, request, url_for
from app.ajsystem.form import _resolve_label
from app.ajsystem.list import List, Field, build_field_config, build_filter_config, build_field_context, get_field, _entidade_fields, _derive_fk_ref
from app.ajsystem.filters import (
    resolve_filters,
    apply_text_filter,
    apply_number_filter,
    apply_boolean_filter,
    apply_select_filter,
    apply_date_filter,
)


def _resolve_model(entity_name: str):
    from app.ajsystem.list import MODEL_MAP
    key = re.sub(r'(?<!^)(?=[A-Z])', '_', entity_name).lower()
    if key in MODEL_MAP:
        return MODEL_MAP[key]
    module_path = f'app.models.{key}'
    try:
        mod = importlib.import_module(module_path)
    except ImportError:
        raise ImportError(f"Modelo não encontrado: {module_path}")
    model = getattr(mod, entity_name, None)
    if model is None:
        raise AttributeError(f"Classe {entity_name} não encontrada em {module_path}")
    return model


def _resolve_cols(fields, entidades, principal=None) -> list:
    """Resolve `List.fields` para configs de campo, espelhando o `Form.fields`:
    - str 'Entidade' → expande todos os campos da entity;
    - 'Entidade.campo' → campo específico;
    - nome simples → campo da entity principal;
    - dict {'name': ..., **cfg} → campo com override.
    """
    if isinstance(fields, str):
        items = [fields]
    else:
        items = fields
    cols = []
    for item in items:
        if isinstance(item, dict):
            name = item.get('name')
            if not name:
                continue
            rest = {k: v for k, v in item.items() if k != 'name'}
            if '.' in name:
                entity, field_name = name.split('.', 1)
                config = entidades.get(entity, {})
            else:
                field_name = name
                config = principal or {}
            base = config.get(field_name, {}) if isinstance(config, dict) else {}
            base = base if isinstance(base, dict) else {}
            cols.append(build_field_config(field_name, {**base, **rest}))
            continue
        if '.' in item:
            entity, field_name = item.split('.', 1)
        else:
            entity = item
            field_name = None
        if field_name:
            if entity in entidades:
                config = entidades[entity]
                cols.append(build_field_config(field_name, config[field_name]))
            elif principal:
                config = principal
                cols.append(build_field_config(entity, config[entity]))
        else:
            config = entidades[entity] if entity in entidades else principal
            for name, cfg in _entidade_fields(config).items():
                cols.append(build_field_config(name, cfg))
    return cols


def _resolve_field_names(items: list) -> list[str]:
    names = []
    for item in items:
        if '.' in item:
            _, field_name = item.split('.', 1)
            names.append(field_name)
        else:
            names.append(item)
    return names


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


def render_list(entity_name: str, module_name: str, data=None, **extra):
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
    new_label = 'Novo ' + _resolve_label(mod, entity_name)

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
