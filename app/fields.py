from dataclasses import dataclass
from typing import Optional


@dataclass
class Field:
    name: str
    label: Optional[str] = None
    width: Optional[int] = None
    align: str = 'left'
    input: str = 'text'
    options: Optional[dict] = None
    filter: Optional[str] = None
    filter_options: Optional[list] = None
    mask: Optional[str] = None
    query: Optional[str] = None
    validate: Optional[list] = None


def field_filter_type(f: Field) -> Optional[str]:
    if f.filter:
        return f.filter
    if f.input == 'boolean':
        return 'boolean'
    if f.input == 'date':
        return 'date'
    if f.input == 'number':
        return 'number'
    return None


def field_filter_options(f: Field) -> Optional[list]:
    if f.filter_options is not None:
        return f.filter_options
    if f.options is not None and f.input == 'select':
        if isinstance(f.options, dict):
            return list(f.options.values())
        return list(f.options)
    return None


def field_to_column(f: Field) -> dict:
    col = {'label': f.label or f.name, 'field': f.name}
    DEFAULT_WIDTHS = {'boolean': 6, 'number': 8, 'date': 12, 'select': 15}
    w = f.width or DEFAULT_WIDTHS.get(f.input, 15)
    label_len = len(col['label'])
    if w < label_len:
        w = label_len
    col['width'] = w
    if f.align != 'left':
        col['align'] = f.align
    ft = field_filter_type(f)
    if ft:
        col['filter'] = ft
    elif f.filter is False:
        col['filter'] = False
    fo = field_filter_options(f)
    if fo:
        col['filter_options'] = fo
    return col


def fields_to_columns(fields: list[Field]) -> list[dict]:
    return [field_to_column(f) for f in fields]


MODEL_MAP: dict[str, type] = {}


def register_model(name: str, model_class: type) -> None:
    MODEL_MAP[name] = model_class


def build_field_context(fields: list[Field], model_map: dict[str, type] | None = None) -> dict:
    from flask import current_app

    if model_map is None:
        model_map = MODEL_MAP
    ctx = {'filter_options': {}}
    with current_app.app_context():
        for f in fields:
            if f.query and f.query in model_map:
                model = model_map[f.query]
                items = model.query.order_by(model.nome).all()
                names = [i.nome for i in items if i.nome]
                if f.filter_options is None:
                    f.filter_options = names
                if f.options is None:
                    f.options = {str(i.id): i.nome for i in items}
    return ctx


def field_grid(f: Field) -> int:
    w = f.width or 12
    if w < 8:
        return 3
    if w < 15:
        return 4
    if w < 25:
        return 6
    return 8


def get_field(fields: list[Field], name: str) -> Optional[Field]:
    for f in fields:
        if f.name == name:
            return f
    return None
