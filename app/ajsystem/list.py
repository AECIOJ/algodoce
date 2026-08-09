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
  link             str        None      Endpoint p/ gerar link (ex: 'orders.edit')
  function         callable   None      Função para valor computado: f(item) -> valor
  rows             int        1         Altura do textarea no form (nº de linhas)
  in_form          bool       True      `False` exclui o campo do form (nem exibe nem submete)
  in_list          int(0|1|2) 1        `0` exclui da listagem/card/filtro; `1` coluna na linha (vai p/ o card quando não couber); `2` sempre no card. `True`→1, `False`→0
  transform        str|callable  auto   Transformação ao salvar: 'title' (padrão em textos editáveis), 'cap', 'upper', 'lower', 'none' ou callable(val, field)

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

from app.ajsystem.constants import CONECTORES

from dataclasses import dataclass, field
from typing import Any, Optional, Callable, Union
from app.ajsystem.filters import FILTER_NUMBER, FILTER_DATE, FILTER_BOOLEAN, FILTER_SELECT
from app.ajsystem.fields import FIELD_TYPES


@dataclass
class Query:
    model: str
    field: str = 'nome'
    columns: Optional[list[str]] = None
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


def _entidade_fields(ent_cfg) -> dict:
    """Campos de uma entrada de `Entity`, ignorando chaves reservadas `__*`

    (ex.: `__meta__` — rótulo/readonly de sessões derivadas).
    """
    return {k: v for k, v in (ent_cfg or {}).items() if not k.startswith('__')}


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
    if transform == 'cap':
        s = val.strip()
        return s[:1].upper() + s[1:] if s else s
    if transform == 'title':
        return _title_case(val.strip())
    if callable(transform):
        return transform(val, field)
    return val


# transform: None | 'none' | 'title' | 'upper' | 'lower' | 'cap' | callable(val, field)
#   None     → auto-inferido por _infer_transform()
#   'none'   → sem transformação (padrão p/ number, boolean, options, edit=False, readonly, hidden)
#   'title'  → primeira letra de cada palavra maiúscula (respeita CONECTORES)
#   'upper'  → tudo maiúsculo
#   'lower'  → tudo minúsculo
#   'cap'    → apenas o 1º caractere em maiúsculo (resto inalterado)
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
    validate: Optional[Union[str, list, Callable]] = None
    decimals: Optional[int] = None
    min: Optional[Union[int, float]] = None
    max: Optional[Union[int, float]] = None
    step: Optional[Union[int, float]] = None
    masterkey: Optional[str] = None
    aggregate: Optional[str] = None
    aggregate_label: Optional[str] = None
    currency: Optional[str] = None
    hide_zero: bool = True
    card_path: Optional[str] = None
    link: Optional[str] = None
    function: Optional[Callable] = None
    required: bool = False
    placeholder: Optional[str] = None
    transform: Any = None
    disabled: bool = False
    readonly: bool = False
    hidden: bool = False
    upload_path: str = ''
    digits_only: bool = False
    attrs: Optional[dict] = None
    in_form: bool = True
    in_list: int = 1
    default: Any = None
    rows: int = 1
    on_set: Optional[Callable] = None
    on_set_ent: Optional[str] = None
    on_set_mod: Optional[str] = None
    calc: Optional[str] = None

    def __post_init__(self):
        if self.in_list is True:
            self.in_list = 1
        elif self.in_list is False:
            self.in_list = 0
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
    def width_ch(self) -> int:
        if self.width is not None:
            return self.width
        if self.mask:
            w = len(self.mask)
            if self.input == 'number' and not self.mask.startswith('-'):
                w += 1
            return w
        return {'boolean': 6, 'checkbox': 6, 'number': 12, 'date': 12, 'image': 12}.get(self.input, 18)


FIELD_DEFAULTS = FIELD_TYPES

_LABEL_OVERRIDES = {
    'id': '#',
    'cpf': 'CPF',
    'cnpj': 'CNPJ',
    'insc_estadual': 'Inscrição Estadual',
    'unidade_medida': 'Und',
    'qtd_minima': 'Qtd. Mín.',
    'prazo_recebimento': 'Prazo',
    'taxa_recebimento': 'Taxa',
    'indice': 'Índice',
    'descricao': 'Descrição',
    'endereco': 'Endereço',
    'telefone': 'Telefone',
    'preco': 'Preço',
}

# Rótulo pt-BR para campos FK (`<stem>_id`), pelo stem do masterkey/query/modelo.
_FK_LABELS = {
    'carteira': 'Carteira',
    'category': 'Categoria',
    'client': 'Cliente',
    'compra': 'Compra',
    'conta': 'Conta',
    'ingredient': 'Insumo',
    'operacao': 'Operação',
    'pai': 'Superior',
    'pedido': 'Pedido',
    'product': 'Produto',
    'quote': 'Orçamento',
    'recurso': 'Recurso',
    'transacao': 'Transação',
}


def _auto_label(name: str) -> str:
    if name in _LABEL_OVERRIDES:
        return _LABEL_OVERRIDES[name]
    if name.endswith('_id'):
        stem = name[:-3]
        return _FK_LABELS.get(stem, stem.capitalize())
    return ' '.join(w.capitalize() for w in name.split('_'))


def _infer_field_from_model(model, name: str) -> dict:
    """Infere tipo/config de um campo a partir da coluna do model (fallback)."""
    if model is None or getattr(model, '__table__', None) is None:
        return {}
    col = model.__table__.columns.get(name)
    if col is None:
        return {}
    cfg = {}
    if next(iter(col.foreign_keys), None) is not None:
        cfg['type'] = 'FK'
        cfg['required'] = not col.nullable
        return cfg
    tname = col.type.__class__.__name__
    if 'Boolean' in tname:
        cfg['type'] = 'BOOL'
    elif 'DateTime' in tname:
        cfg['type'] = 'DATA_HORA'
    elif 'Date' in tname:
        cfg['type'] = 'DATA'
    elif 'Time' in tname:
        cfg['type'] = 'HORA'
    elif tname in ('Integer', 'SmallInteger', 'BigInteger'):
        cfg['type'] = 'INT'
    elif tname in ('Numeric', 'Float'):
        cfg['type'] = 'NUM'
    elif tname == 'Text':
        cfg['type'] = 'MEMO'
    elif tname == 'String':
        cfg['type'] = 'TEXT'
    cfg['required'] = not col.nullable
    return cfg


def _derive_fk_ref(f: Field, model) -> Field:
    """Preenche query/card_path/filter_path de um FK a partir da relação do model."""
    if f.query or f.masterkey or f.options is not None:
        return f
    if not f.name.endswith('_id') or model is None:
        return f
    mapper = getattr(model, '__mapper__', None)
    if mapper is None:
        return f
    stem = f.name[:-3]
    rel = None
    rel_name = None
    if stem in mapper.relationships:
        rel = mapper.relationships[stem]
        rel_name = stem
    else:
        for rname, r in mapper.relationships.items():
            cols = getattr(r, 'local_columns', None)
            if cols and any(c.name == f.name for c in cols):
                rel = r
                rel_name = rname
                break
    if rel is None:
        return f
    target = rel.mapper.class_
    key = _model_key(target)
    if key is None:
        return f
    f.query = key
    display = 'nome' if hasattr(target, 'nome') else 'descricao'
    if not f.card_path:
        f.card_path = f'{rel_name}.{display}'
    if not f.filter_path:
        f.filter_path = f'{rel_name}.{display}'
    return f


def build_field_config(name: str, cfg: dict) -> dict:
    field_type = cfg.get('type', 'TEXT')
    defaults = FIELD_DEFAULTS.get(field_type, {})
    if 'type' not in cfg:
        defaults = {k: v for k, v in defaults.items() if k != 'required'}
    props = {**defaults, **cfg, 'name': name}
    props.pop('type', None)

    if 'label' not in props:
        props['label'] = _auto_label(name)

    mk = props.pop('masterkey', None)
    if mk:
        props.setdefault('query', mk)
        rel_name = name[:-3] if name.endswith('_id') else name
        props.setdefault('card_path', f'{rel_name}.nome')
        props.setdefault('filter_path', f'{rel_name}.nome')

    if 'list' in props:
        props['options'] = props.pop('list')

    if props.get('input') == 'multi' and props.get('options'):
        for k in props['options']:
            if len(str(k)) != 1:
                raise ValueError(
                    f"MULT10: opção '{k}' de '{name}' deve ter código de 1 caractere (0-9)"
                )
        if len(props['options']) > 10:
            raise ValueError(f"MULT10: campo '{name}' suporta no máximo 10 opções (0-9)")

    if 'mask' not in props and 'decimals' in props:
        d = props['decimals']
        if d == 0:
            props['mask'] = '9999'
        else:
            props['mask'] = f'9999.{"9" * d}'

    return props


def _infer_transform(f: Field) -> str:
    if f.transform is not None:
        return f.transform
    if not f.in_form or f.readonly or f.hidden:
        return 'none'
    if f.input in ('number', 'boolean', 'checkbox', 'date', 'time', 'image'):
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
    if f.digits_only:
        col['digits_only'] = True
    if f.decimals is not None:
        col['decimals'] = f.decimals
    if f.currency:
        col['currency'] = f.currency
    if f.hide_zero:
        col['hide_zero'] = True
    if f.card_path:
        col['card_path'] = f.card_path
    if f.options:
        col['options'] = f.options
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
    return [field_to_column(f) for f in fields]


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
            field_list = [Field(name=k, **v) for k, v in _entidade_fields(fields).items()]
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
            cfg.setdefault('label', f.display_label)
            config[f.name] = cfg
            continue

        ftype = f.filter if isinstance(f.filter, str) else field_filter_type(f)
        if not ftype:
            continue

        cfg = {'type': ftype, 'modes': FILTER_MODES.get(ftype, [])}
        cfg['label'] = f.display_label
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


def _model_key(model_class):
    """Chave registrada de um modelo em `MODEL_MAP` (por classe), ou None."""
    for key, cls in MODEL_MAP.items():
        if cls is model_class:
            return key
    return None


def _fk_query_for(child_model, field_name):
    """Deriva a chave `query` (registrada em MODEL_MAP) de um campo `*_id`.

    Usa a relação do modelo filho que referencia essa coluna. Retorna None
    quando não há relação correspondente ou o alvo não está registrado.
    """
    if not field_name.endswith('_id') or child_model is None:
        return None
    mapper = getattr(child_model, '__mapper__', None)
    if mapper is None:
        return None
    stem = field_name[:-3]
    rel = mapper.relationships.get(stem)
    if rel is None:
        for r in mapper.relationships.values():
            cols = getattr(r, 'local_columns', None)
            if cols and any(c.name == field_name for c in cols):
                rel = r
                break
    if rel is None or rel.mapper is None:
        return None
    return _model_key(rel.mapper.class_)


def build_field_context(fields: list[Field] | dict) -> dict:
    from flask import current_app

    if isinstance(fields, dict):
        if 'fields' in fields:
            fields = _resolve_fieldset(fields)
        else:
            fields = [Field(name=k, **v) for k, v in _entidade_fields(fields).items()]
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
    template: Optional[str] = None
    linha: Optional[list[int]] = None
    card_idx: Optional[list[int]] = None

    def __post_init__(self):
        if isinstance(self.fields, dict):
            if 'fields' in self.fields:
                self.fields = _resolve_fieldset(self.fields, self.extra)
            else:
                self.fields = [Field(name=k, **v) for k, v in self.fields.items()]

    @property
    def master_fields(self):
        if self.fields_master is not None:
            return [self.fields[i-1] for i in self.fields_master]
        return self.fields

    @property
    def detail_fields(self):
        if self.fields_detail:
            return [self.fields[i-1] for i in self.fields_detail]
        return None

    @property
    def linha_fields(self):
        if self.linha:
            return [self.master_fields[i] for i in self.linha]
        return self.master_fields

    @property
    def card_fields(self):
        if self.card_idx:
            return [self.fields[i-1] for i in self.card_idx]
        return None
