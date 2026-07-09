from dataclasses import dataclass
from typing import Optional, Callable


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
    aggregate: Optional[str] = None
    aggregate_label: Optional[str] = None
    currency: Optional[str] = None
    hide_zero: bool = True
    card_path: Optional[str] = None
    pos: Optional[int] = None
    link: Optional[str] = None
    function: Optional[Callable] = None


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
    col = {'label': f.label or f.name, 'field': f.name, 'input': f.input}
    DEFAULT_WIDTHS = {'boolean': 6, 'number': 8, 'date': 12, 'select': 15}
    w = f.width or DEFAULT_WIDTHS.get(f.input, 15)
    largest_word = max(len(w) for w in (f.label or f.name).split())
    if w < largest_word:
        w = largest_word
    col['width'] = w + 1
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
    if f.mask:
        col['mask'] = f.mask
    if f.currency:
        col['currency'] = f.currency
    if f.hide_zero:
        col['hide_zero'] = True
    if f.card_path:
        col['card_path'] = f.card_path
    if f.options:
        col['options'] = f.options
    if f.pos is not None:
        col['pos'] = f.pos
    elif f.name == 'id':
        col['pos'] = 0
    else:
        col['pos'] = 9
    if f.link:
        col['link'] = f.link
    if f.function:
        col['function'] = f.function
    if f.aggregate:
        col['aggregate'] = f.aggregate
        if f.aggregate_label:
            col['aggregate_label'] = f.aggregate_label
    return col


def fields_to_columns(fields: list[Field]) -> list[dict]:
    cols = [field_to_column(f) for f in fields]
    return [c for _, c in sorted(enumerate(cols), key=lambda x: (x[1]['pos'], x[0]))]


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
