"""
XXX_TABLE / XXX_FIELDS — Configuração de tabelas e campos de listagem.

Cada rota sys_*.py declara:
  XXX_FIELDS = [Field(...), ...]          # lista de campos
  XXX_TABLE  = Table(fields=XXX_FIELDS, ...)  # config da tabela

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
 Table — configuração da tabela
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
   Table(fields=FIELDS, fields_master=[1,2,3], fields_detail=[4,5,6],
         master_key='compra_id', edit_endpoint='compras.edit')
"""
from dataclasses import dataclass, field
from typing import Any, Optional, Callable


def _auto_label(name: str) -> str:
    s = name[:-3] if name.endswith('_id') else name
    s = s.replace('_', ' ')
    return s[0].upper() + s[1:] if s else name


@dataclass
class Field:
    name: str
    label: Optional[str] = None
    width: Optional[int] = None
    align: str = 'left'
    input: str = 'text'
    options: Optional[dict] = None
    filter: Optional[str] = None
    filter_options: Any = field(default=None)
    mask: Optional[str] = None
    query: Optional[str] = None
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
    disabled: bool = False
    attrs: Optional[dict] = None

    @property
    def display_label(self) -> str:
        return self.label or _auto_label(self.name)


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


def field_filter_options(f: Field):
    if f.filter_options is not None:
        return f.filter_options
    if f.options is not None and f.input == 'select':
        if isinstance(f.options, dict):
            return f.options
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


def build_field_context(fields: list[Field], model_map: dict[str, type] | None = None, filters_config: dict | None = None) -> dict:
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
                if filters_config and f.name in filters_config:
                    fcfg = filters_config[f.name]
                    if fcfg.get('type') == 'select' and 'options' not in fcfg:
                        ctx['filter_options'][f.name] = [i.nome for i in items if i.nome]
            ft = field_filter_type(f)
            if ft == 'select':
                fo = field_filter_options(f)
                if fo is not None and f.name not in ctx['filter_options']:
                    ctx['filter_options'][f.name] = fo
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


@dataclass
class Table:
    fields: list[Field]
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
