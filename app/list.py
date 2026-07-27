"""
XXX_LIST / XXX_FIELDS — Configuração de listas e campos de listagem.

Cada rota sys_*.py declara:
  XXX_FIELDS = [Field(...), ...]          # lista de campos
  XXX_LIST   = List(fields=XXX_FIELDS, ...)  # config da lista

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Field — configuração de uma coluna
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 Campo            Tipo       Default   Descrição
 ──────────────── ────────── ───────── ──────────────────────────────────
 name             str        (obrig.)  Nome do campo (chave do dict)
 label            str        name      Título da coluna
 width            int        auto      Largura em caracteres (ch)
 align            str        'left'    'left' | 'right' | 'center'
 input            str        'text'    Tipo do campo (define filtro auto):
                                        'text'    → filtro texto
                                        'number'  → filtro numérico
                                        'date'    → filtro data
                                        'boolean' → filtro Sim/Não
                                        'select'  → filtro select
 options          dict       None      Opções para select: {chave: label}
 filter           str|False  auto      Tipo do filtro forçado, ou False p/ desabilitar
 filter_options   list       None      Opções customizadas para o filtro select
 mask             str        None      Máscara de formatação (ex: '999.999')
 query            str        None      Chave do MODEL_MAP p/ popular options do banco
 validate         list       None      Regras de validação no form
 aggregate        str        None      'sum' p/ exibir total no rodapé
 aggregate_label  str        None      Label do total (ex: 'Total Geral')
 currency         str        None      'brl' p/ formatar como moeda R$
 hide_zero        bool       True      Ocultar valor zero
 card_path        str        None      Acesso aninhado (ex: 'conta.nome')
 pos              int        9         Ordem da coluna (0=ID, 9=último)
 link             str        None      Endpoint p/ gerar link (ex: 'orders.edit')
 function         callable   None      Função para valor computado: f(item) -> valor

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 List — configuração da lista
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 Campo              Tipo       Default   Descrição
 ────────────────── ────────── ───────── ──────────────────────────────────
 fields             list       (obrig.)  Lista de Field
 fields_master      list[int]  None      Índices 1-based dos campos mestre (master-detail)
 fields_detail      list[int]  None      Índices 1-based dos campos detalhe (master-detail)
 master_key         str        None      Campo para groupby no master-detail
 edit_endpoint      str        None      Endpoint de edição (ex: 'orders.edit')
 edit_id_field      str        'id'      Campo que contém o ID para edição
 edit_if_field      str        None      Só exibe edição se este campo for não-nulo
 edit_endpoint_map  dict       None      Mapa de endpoints por tipo
 edit_endpoint_key  str        None      Chave do item para lookup no edit_endpoint_map
 detail_data        str        None      Atributo com sub-itens do detalhe
 reports            list       None      Lista de Report vinculados

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Exemplos
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 Simples:
   Field(name='nome', label='Nome', width=20, pos=1)

 Select do banco:
   Field(name='categoria', label='Categoria', width=15, query='category')

 Master-detail:
   List(fields=FIELDS, fields_master=[1,2,3], fields_detail=[4,5,6],
        master_key='compra_id', edit_endpoint='compras.edit')
"""
from sqlalchemy import text

from app.constants import CONECTORES

from dataclasses import dataclass, field
from typing import Any, Optional, Callable, Union


@dataclass
class Query:
    model: str
    field: str = 'nome'
    colunas: Optional[list[str]] = None
    when: Optional[str] = None
    order: Optional[str] = None


def _resolve_query(q: Any) -> Optional[Query]:
    if q is None:
        return None
    if isinstance(q, Query):
        return q
    if isinstance(q, str):
        return Query(model=q)
    if isinstance(q, dict):
        return Query(**q)
    return None


def _resolve_fieldset(fieldset, extra=None):
    """Converte dict FieldSet em lista de Field objects.

    fieldset = {'model': Model, 'fields': {name: {cfg}, ...}}  ou
               {'model': Model, 'fields': [{name: ..., ...}, ...]}
    extra = {name: {override_cfg}, ...}  (overrides contextuais)
    """
    raw = fieldset.get('fields', {})
    extra = extra or {}
    result = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, Field):
                result.append(item)
            elif isinstance(item, dict):
                name = item.get('name')
                if name:
                    rest = {k: v for k, v in item.items() if k != 'name'}
                    merged = {**rest, **extra.get(name, {})}
                    result.append(Field(name=name, **merged))
    else:
        for name, cfg in raw.items():
            merged = {**cfg, **extra.get(name, {})}
            result.append(Field(name=name, **merged))
    return result


def _auto_label(name: str) -> str:
    s = name[:-3] if name.endswith('_id') else name
    s = s.replace('_', ' ')
    return _title_case(s) if s else name


def _title_case(text: str) -> str:
    words = text.strip().split()
    result = []
    for i, w in enumerate(words):
        if i > 0 and w.lower() in CONECTORES:
            result.append(w.lower())
        else:
            result.append(w[0].upper() + w[1:].lower() if w else w)
    return " ".join(result)


def _apply_transform(val, transform, field=None):
    if not val or not isinstance(val, str):
        return val
    if transform == 'upper':
        return val.strip().upper()
    if transform == 'lower':
        return val.strip().lower()
    if transform == 'title':
        return _title_case(val.strip())
    if callable(transform):
        return transform(val, field)
    return val


# transform: None | 'none' | 'title' | 'upper' | 'lower' | callable(val, field)
#   None     → auto-inferido por _infer_transform()
#   'none'   → sem transformação (padrão p/ number, boolean, options, edit=False)
#   'title'  → primeira letra de cada palavra maiúscula (respeita CONECTORES)
#   'upper'  → tudo maiúsculo
#   'lower'  → tudo minúsculo
#   callable → função customizada (val, field) -> transformed_val
@dataclass
class Field:
    name: str
    label: Optional[str] = None
    width: Optional[int] = None
    grid: Optional[int] = None
    align: str = 'left'
    input: str = 'text'
    options: Optional[dict] = None
    filter: Any = None
    filter_options: Any = field(default=None)
    filter_path: Optional[str] = None
    mask: Optional[str] = None
    query: Optional[Union[str, dict, Query]] = None
    query_filter: Optional[dict] = None
    validate: Optional[list] = None
    aggregate: Optional[str] = None
    aggregate_label: Optional[str] = None
    currency: Optional[str] = None
    hide_zero: bool = True
    card_path: Optional[str] = None
    pos: Optional[int] = None
    link: Optional[str] = None
    function: Optional[Callable] = None
    required: bool = False
    placeholder: Optional[str] = None
    transform: Any = None
    disabled: bool = False
    attrs: Optional[dict] = None
    edit: bool = True
    default: Any = None

    def __post_init__(self):
        if self.width is None and self.mask:
            self.width = len(self.mask)
            if self.input == 'number' and not self.mask.startswith('-'):
                self.width += 1
        if self.input == 'number' and self.align == 'left':
            self.align = 'right'

    @property
    def display_label(self) -> str:
        return self.label or _auto_label(self.name)

    @property
    def form_edit(self) -> bool:
        return self.edit is True


def _infer_transform(f: Field) -> str:
    if f.transform is not None:
        return f.transform
    if not f.edit:
        return 'none'
    if f.input in ('number', 'boolean', 'checkbox', 'date', 'time'):
        return 'none'
    if f.options:
        return 'none'
    return 'title'


def apply_field_transforms(instance, fields):
    field_list = fields
    if isinstance(fields, dict):
        if 'fields' in fields:
            field_list = _resolve_fieldset(fields)
        else:
            field_list = [Field(name=k, **v) for k, v in fields.items()]
    for f in field_list:
        if not hasattr(instance, f.name):
            continue
        val = getattr(instance, f.name, None)
        if val is None or not isinstance(val, str):
            continue
        tr = _infer_transform(f)
        if tr == 'none':
            continue
        setattr(instance, f.name, _apply_transform(val, tr, f))


def field_filter_type(f: Field) -> Optional[str]:
    if f.filter is not None:
        if isinstance(f.filter, dict):
            return f.filter.get('type')
        if isinstance(f.filter, str):
            return f.filter
        if f.filter is False:
            return None
    if f.input == 'boolean':
        return 'boolean'
    if f.input == 'date':
        return 'date'
    if f.input == 'number':
        return 'number'
    if f.input == 'select':
        return 'select'
    if f.options is not None:
        return 'select'
    if f.filter_options is not None:
        return 'select'
    if f.query is not None:
        return 'select'
    return 'text'


def field_filter_options(f: Field):
    if f.filter_options is not None:
        return f.filter_options
    if f.options is not None:
        if isinstance(f.options, dict):
            return list(f.options.values())
        return list(f.options)
    q = _resolve_query(f.query)
    if q is not None:
        try:
            model = MODEL_MAP.get(q.model)
            if model and hasattr(model, 'query'):
                query = model.query
                if q.when:
                    query = query.filter(text(q.when))
                items = query.order_by(q.order or q.field).all()
                return [str(getattr(o, q.field, o)) for o in items if getattr(o, q.field, None)]
        except Exception:
            pass
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


FILTER_MODES = {
    'text': [('igual', 'Igual a'), ('contains', 'Contém'), ('starts', 'Começa')],
    'number': [('igual', 'Igual a'), ('entre', 'Entre'),
               ('maior_que', 'Maior que'), ('maior_igual', 'Maior ou igual a'),
               ('menor_que', 'Menor que'), ('menor_igual', 'Menor ou igual a')],
    'date': [('hoje', 'Hoje'), ('periodo', 'Período'), ('ontem', 'Ontem'),
             ('ultimos_7_dias', 'Últimos 7 dias'), ('mes', 'Mês'),
             ('mes_atual', 'Mês Atual'), ('mes_anterior', 'Mês Anterior'),
             ('ano', 'Ano'), ('ano_atual', 'Ano Atual'),
             ('a_partir_de', 'A partir de'), ('ate_a_data_de', 'Até a data de')],
    'boolean': [('', 'Todos'), ('true', 'Sim'), ('false', 'Não')],
    'select': [],
}


def build_filter_config(fields):
    if isinstance(fields, dict):
        if 'fields' in fields:
            field_list = _resolve_fieldset(fields)
        else:
            field_list = [Field(name=k, **v) for k, v in fields.items()]
    else:
        field_list = fields

    config = {}
    for f in field_list:
        if f.filter is False:
            continue

        if isinstance(f.filter, dict):
            cfg = {**f.filter}
            if cfg.get('type') == 'select' and 'options' not in cfg:
                opts = field_filter_options(f)
                if opts:
                    cfg['options'] = opts
            if f.filter_path:
                cfg['filter_path'] = f.filter_path
            config[f.name] = cfg
            continue

        ftype = f.filter if isinstance(f.filter, str) else field_filter_type(f)
        if not ftype:
            continue

        cfg = {'type': ftype, 'modes': FILTER_MODES.get(ftype, [])}
        if ftype == 'select':
            opts = field_filter_options(f)
            if opts:
                cfg['options'] = opts if isinstance(opts, list) else list(opts.values()) if isinstance(opts, dict) else opts
        if f.filter_path:
            cfg['filter_path'] = f.filter_path
        config[f.name] = cfg

    return config


MODEL_MAP: dict[str, type] = {}


def register_model(name: str, model_class: type) -> None:
    MODEL_MAP[name] = model_class


def build_field_context(fields: list[Field] | dict) -> dict:
    from flask import current_app

    if isinstance(fields, dict):
        if 'fields' in fields:
            fields = _resolve_fieldset(fields)
        else:
            fields = [Field(name=k, **v) for k, v in fields.items()]
    ctx = {'filter_options': {}}
    with current_app.app_context():
        for f in fields:
            q = _resolve_query(f.query)
            if q is not None:
                model = MODEL_MAP.get(q.model)
                if model and hasattr(model, 'query'):
                    query = model.query
                    if q.when:
                        query = query.filter(text(q.when))
                    items = query.order_by(q.order or q.field).all()
                    names = [str(getattr(o, q.field, o)) for o in items if getattr(o, q.field, None)]
                    if f.filter_options is None:
                        f.filter_options = names
                    if f.options is None:
                        f.options = {str(getattr(o, 'id', o)): str(getattr(o, q.field, o)) for o in items if getattr(o, q.field, None)}
            ft = field_filter_type(f)
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


def get_field(fields: list[Field], name: str) -> Optional[Field]:
    for f in fields:
        if f.name == name:
            return f
    return None


@dataclass
class List:
    fields: Union[list, dict]
    fields_master: Optional[list[int]] = None
    fields_detail: Optional[list[int]] = None
    master_key: Optional[str] = None
    edit_endpoint: Optional[str] = None
    edit_id_field: str = 'id'
    edit_if_field: Optional[str] = None
    edit_endpoint_map: Optional[dict] = None
    edit_endpoint_key: Optional[str] = None
    detail_data: Optional[str] = None
    send_endpoint: Optional[str] = None
    reports: Optional[list] = None
    extra: Optional[dict] = None

    def __post_init__(self):
        if isinstance(self.fields, dict):
            if 'fields' in self.fields:
                self.fields = _resolve_fieldset(self.fields, self.extra)
            else:
                self.fields = [Field(name=k, **v) for k, v in self.fields.items()]

    @property
    def master_fields(self):
        if self.fields_master:
            return [self.fields[i-1] for i in self.fields_master]
        return self.fields

    @property
    def detail_fields(self):
        if self.fields_detail:
            return [self.fields[i-1] for i in self.fields_detail]
        return None
