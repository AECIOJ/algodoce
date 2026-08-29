"""LIST — resolução de colunas, filtros e contexto de listagem.

Reescrito do zero observando `core/old/list.py`. Consome a resolução declarativa
de `defs.data` (merged `Entity(model)`+`Schema`). Helpers data-agnósticos para a
renderização de `pages/list.html` (cujos contratos são mantidos).
"""
import re
from dataclasses import dataclass, field as dc_field
from typing import Optional, Union

from app.ajsystem.defs.buttons import resolve_buttons as _resolve_buttons
from app.ajsystem.defs.data import (
    Field, _resolve_fieldset, _entidade_fields, build_field, build_field_config,
    get_field,
)


@dataclass
class List:
    """Config de listagem — objeto consumido por `pages/list.html`."""
    fields: Union[list, dict]
    fields_master: Optional[list] = None
    edit_endpoint: Optional[str] = None
    edit_id_field: str = 'id'
    detail_data: Optional[str] = None
    buttons: Optional[list] = None
    template: Optional[str] = None
    linha: Optional[list] = None
    card_idx: Optional[list] = None
    tags: Optional[list] = None

    def __post_init__(self):
        if isinstance(self.fields, dict):
            if 'fields' in self.fields:
                self.fields = _resolve_fieldset(self.fields)
            else:
                self.fields = [Field(name=k, **v) for k, v in _entidade_fields(self.fields).items()]

    def resolve_buttons(self, bp_name=None):
        return _resolve_buttons(self.buttons, bp_name)

    @property
    def master_fields(self):
        if self.fields_master is not None:
            return [self.fields[i - 1] for i in self.fields_master]
        return self.fields

    @property
    def card_fields(self):
        if self.card_idx:
            return [self.fields[i - 1] for i in self.card_idx]
        return None


def infer_filter_type(f: Field):
    inf = f.in_filter
    if inf == 0:
        return None
    if inf == 1:
        if f.input in ('date', 'datetime-local'):
            return 'date'
        if f.input == 'number':
            return 'number'
        if f.input == 'boolean':
            return 'boolean'
        return 'text'
    if inf == 2:
        return 'boolean' if f.input == 'boolean' else 'select'
    if inf == 3:
        return 'checklist'
    if f.input == 'boolean':
        return 'boolean'
    if f.input in ('date', 'datetime-local'):
        return 'date'
    if f.input == 'number':
        return 'number'
    if f.input == 'multi':
        return None
    if f.input == 'select' or f.options is not None or f.query is not None:
        return 'select'
    return 'text'


def field_filter_options(f: Field):
    if f.options is not None:
        if isinstance(f.options, dict):
            return list(f.options.values())
        return list(f.options)
    return None


def field_to_column(f: Field) -> dict:
    col = {'label': f.label or f.name, 'field': f.name, 'input': f.input}
    DEFAULT_WIDTHS = {'boolean': 6, 'number': 8, 'date': 12, 'select': 15}
    w = f.width or DEFAULT_WIDTHS.get(f.input, 15)
    largest_word = max(len(x) for x in (f.label or f.name).split()) if (f.label or f.name) else 3
    if w < largest_word:
        w = largest_word
    col['width'] = w + 1
    if f.align != 'left':
        col['align'] = f.align
    ft = infer_filter_type(f)
    if ft:
        col['filter'] = ft
    elif f.in_filter == 0:
        col['filter'] = False
    fo = field_filter_options(f)
    if fo:
        col['filter_options'] = fo
    if f.mask:
        col['mask'] = f.mask
    if f.digits_only:
        col['digits_only'] = True
    if f.decimals is not None:
        col['decimals'] = f.decimals
    if f.currency:
        col['currency'] = f.currency
    if f.percent:
        col['percent'] = True
    if f.hide_zero:
        col['hide_zero'] = True
    if f.options:
        col['options'] = f.options
    if f.link:
        col['link'] = f.link
    if f.calc:
        col['calc'] = f.calc
    return col


def fields_to_columns(fields: list[Field]) -> list[dict]:
    return [field_to_column(f) for f in fields]


FILTER_MODES = {
    'text': [('igual', 'Igual a'), ('contains', 'Contém'), ('starts', 'Começa')],
    'number': [('igual', 'Igual a'), ('entre', 'Entre'),
               ('maior_que', 'Maior que'), ('maior_igual', 'Maior ou igual a'),
               ('menor_que', 'Menor que'), ('menor_igual', 'Menor ou igual a')],
    'date': [('hoje', 'Hoje'), ('ontem', 'Ontem'),
             ('ultimos_7_dias', 'Últimos 7 dias'),
             ('mes_atual', 'Mês Atual'), ('mes_anterior', 'Mês Anterior'),
             ('mes', 'Mês'), ('mes_ano', 'Mês/Ano'), ('ano_atual', 'Ano Atual'),
             ('ano_anterior', 'Ano Anterior'), ('ano', 'Ano'),
             ('ate_a_data_de', 'Até a data de'), ('a_partir_de', 'A partir de'),
             ('periodo', 'Período')],
    'boolean': [('', 'Todos'), ('true', 'Sim'), ('false', 'Não')],
    'select': [],
    'checklist': [],
}


def build_filter_config(fields):
    if isinstance(fields, dict):
        if 'fields' in fields:
            field_list = _resolve_fieldset(fields)
        else:
            field_list = [Field(name=k, **v) for k, v in _entidade_fields(fields).items()]
    else:
        field_list = fields

    config = {}
    for f in field_list:
        ftype = infer_filter_type(f)
        if not ftype:
            continue
        cfg = {'type': ftype, 'modes': FILTER_MODES.get(ftype, [])}
        cfg['label'] = f.display_label
        if ftype in ('select', 'checklist'):
            opts = field_filter_options(f)
            if opts:
                cfg['options'] = opts
        config[f.name] = cfg
    return config


def build_field_context(fields) -> dict:
    """Contexto de filtros/opções (estrutura mínima consumida pelo template)."""
    if isinstance(fields, dict):
        if 'fields' in fields:
            fields = _resolve_fieldset(fields)
        else:
            fields = [Field(name=k, **v) for k, v in _entidade_fields(fields).items()]
    ctx = {'filter_options': {}}
    for f in fields:
        ft = infer_filter_type(f)
        if ft == 'select':
            fo = field_filter_options(f)
            if fo is not None and f.name not in ctx['filter_options']:
                ctx['filter_options'][f.name] = fo
    return ctx


def field_grid(f: Field) -> int:
    if f.grid:
        return f.grid
    if f.input == 'textarea':
        return 12
    if f.input in ('boolean', 'checkbox'):
        return 2
    w = f.width or 12
    if w <= 4:
        return 2
    if w <= 8:
        return 3
    if w <= 14:
        return 4
    if w <= 24:
        return 6
    return 8


def _resolve_model(entity_name: str):
    from app.ajsystem.defs.data import MODEL_MAP
    key = re.sub(r'(?<!^)(?=[A-Z])', '_', entity_name).lower()
    if key in MODEL_MAP:
        return MODEL_MAP[key]
    import importlib
    module_path = f'app.models.{key}'
    try:
        mod = importlib.import_module(module_path)
    except ImportError:
        raise ImportError(f"Modelo não encontrado: {module_path}")
    model = getattr(mod, entity_name, None)
    if model is None:
        raise AttributeError(f"Classe {entity_name} não encontrada em {module_path}")
    return model


def resolve_column_configs(merged_entity: dict, spec, principal=None) -> list:
    """Resolve `spec` (str/de lista) para configs de campo a partir da entity
    merged `{campo: cfg}` (mesma semântica de `_resolve_cols` do legado).

    `str` bare = nome de uma entidade → expande todos os campos da entity
    merged (config = principal ou merged). `str`/item com `.` → campo específico.
    """
    config = principal or merged_entity
    if isinstance(spec, str):
        if spec in config:
            spec = [spec]
        else:
            # Mantém a ordem em que os campos foram definidos no dicionário (Python 3.7+ dict preserva ordem)
            spec = list((config or {}).keys())
    cols = []
    for item in spec or []:
        if isinstance(item, dict):
            name = (item.get('name') or '').split('.', 1)[-1]
            if not name:
                continue
            rest = {k: v for k, v in item.items() if k != 'name'}
            base = config.get(name, {}) or {}
            base = base if isinstance(base, dict) else {}
            cols.append(build_field(name, {**base, **rest}))
            continue
        field_name = item.split('.', 1)[-1]
        base = config.get(field_name, {}) or {}
        base = base if isinstance(base, dict) else {}
        cols.append(build_field(field_name, base))
    return cols
