"""DATA — camada declarativa de dados (Field, Entity→Schema) do framework.

Reúne:
- o dataclass `Field` e a tabela de tipos `FIELD_TYPES`;
- a construção do config/`Field` a partir de uma entrada (build_field_config);
- a resolução das variáveis declarativas `Entity` (definição no model) e
  `Schema` (overrides por página na rota), com validação fail-fast de chaves;
- o registro de models (`MODEL_MAP`) usado pela resolução declarativa.

Regra de merge por campo: `Entity[field] ∪ Schema[entidade][field]`, o que vier
no `Schema` vence. Se o model não tem `Entity`, o `Schema`/config da rota vale
integral (compat com o modelo legado).

Esta camada NÃO importa `query` (a espec `Query`/FK entra depois, quando uma
página precisar). Aqui `query` permanece apenas como config crua.
"""
import importlib
import re
from dataclasses import dataclass, fields as dc_fields
from typing import Any, Callable, Optional, Union


# ── Tipos base de campo ──────────────────────────────────────────────────────
FIELD_TYPES = {
    'TEXT':      {'input': 'text'},
    'MEMO':      {'input': 'textarea'},
    'INT':       {'input': 'number', 'align': 'right', 'width': 5, 'decimals': 0},
    'NUM':       {'input': 'number', 'align': 'right', 'width': 10, 'decimals': 2},
    'PERCENT':   {'input': 'number', 'align': 'right', 'width': 6, 'decimals': 1, 'min': 0, 'max': 100, 'percent': True},
    'ID':        {'input': 'number', 'in_form': 0, 'label': '#'},
    'DK':        {'input': 'number', 'in_form': 0, 'in_filter': 0},
    'DATA':      {'input': 'date'},
    'DATA_HORA': {'input': 'datetime-local'},
    'HORA':      {'input': 'time'},
    'BOOL':      {'input': 'boolean'},
    'FONE':      {'input': 'text', 'mask': '(99) 99999-9999', 'digits_only': True},
    'CPF':       {'input': 'text', 'mask': '999.999.999-99', 'digits_only': True, 'validate': 'cpf'},
    'CNPJ':      {'input': 'text', 'mask': '99.999.999/9999-99', 'digits_only': True, 'validate': 'cnpj'},
    'FK':        {'input': 'select'},
    'LIST':      {'input': 'select'},
    'MULT10':    {'input': 'multi', 'in_filter': 0},
    'IMAGE':     {'input': 'image', 'in_filter': 0, 'required': False, 'upload_path': ''},
}

# `required` é sempre opt-in: declarado na Entity/Schema via 'required': True.


def fmt_mask(value, mask):
    """Aplica `mask` a `value`. Tolerante: extrai dígitos antes de formatar."""
    if value is None:
        return ''
    digits = re.sub(r'\D', '', str(value))
    if not mask:
        return digits
    out = []
    di = 0
    for ch in mask:
        if ch == '9':
            if di < len(digits):
                out.append(digits[di])
                di += 1
            else:
                break
        else:
            out.append(ch)
    return ''.join(out)


def _auto_label(name: str) -> str:
    if name.endswith('_id'):
        return name[:-3].capitalize()
    return ' '.join(w.capitalize() for w in name.split('_'))


# ── Dataclass Field (runtime resolvido) ──────────────────────────────────────
@dataclass
class Query:
    """Especificação declarativa de consulta (usada em List e Report)."""
    columns: Union[str, list, dict, None] = None
    join: Optional[Union[str, list, dict]] = None
    when: Optional[Union[str, dict, Callable]] = None
    groups: Optional[Union[str, list[str]]] = None
    order: Optional[Union[str, list[str]]] = None
    limit: Optional[int] = None


@dataclass
class Table:
    """Especificação de tabela editável (Master-Detail) em sessões de formulário."""
    columns: Union[str, list, dict, None] = None
    allow_add: bool = True
    allow_delete: bool = True
    order: Optional[Union[str, list[str]]] = None


@dataclass
class Session:
    """Especificação de uma sessão filha (bloco) em um Formulário (`Form`).
    
    Se `template` for fornecido, ele é renderizado diretamente e as demais
    propriedades são ignoradas. Caso contrário, contém obrigatoriamente
    `query` (somente leitura) OU `table` (editável).
    """
    template: Optional[str] = None
    name: Optional[str] = None
    fields: Union[str, list, dict, None] = None
    query: Optional[dict] = None
    table: Optional[Union[dict, Table]] = None

    def __post_init__(self):
        if self.template:
            return
        if not self.name:
            raise ValueError("Session: 'name' é obrigatório quando 'template' não é fornecido.")
        if self.query is not None and self.table is not None:
            raise ValueError(f"Sessão '{self.name}': defina 'query' OU 'table', não ambas na mesma sessão.")


@dataclass
class Field:
    name: str
    label: Optional[str] = None
    width: Optional[int] = None
    grid: Optional[int] = None
    align: str = 'left'
    input: str = 'text'
    options: Optional[dict] = None
    in_filter: Optional[int] = None
    mask: Optional[str] = None
    query: Any = None          # config crua (str/dict); Query entra posteriormente
    validate: Optional[Union[str, list, Callable]] = None
    decimals: Optional[int] = None
    min: Optional[Union[int, float]] = None
    max: Optional[Union[int, float]] = None
    step: Optional[Union[int, float]] = None
    derived: Optional[dict] = None
    currency: Optional[str] = None
    percent: bool = False
    hide_zero: bool = True
    link: Optional[str] = None
    required: bool = False
    mastermodel: Optional[Any] = None
    lookup: Optional[str] = None
    placeholder: Optional[str] = None
    help: Any = None
    transform: Any = None
    disabled: bool = False
    readonly: bool = False
    hidden: bool = False
    upload_path: str = ''
    digits_only: bool = False
    attrs: Optional[dict] = None
    in_form: int = 1
    in_list: int = 1
    default: Any = None
    rows: int = 1
    on_set: Optional[Callable] = None
    on_set_ent: Optional[str] = None
    on_set_mod: Optional[str] = None
    calc: Optional[Union[str, Callable]] = None

    def __post_init__(self):
        if self.in_filter is True:
            self.in_filter = 1
        elif self.in_filter is False:
            self.in_filter = 0
        if self.in_form is True:
            self.in_form = 1
        elif self.in_form is False:
            self.in_form = 0
        if self.in_list is True:
            self.in_list = 1
        elif self.in_list is False:
            self.in_list = 0
        if self.width is None and self.mask:
            self.width = len(self.mask)
            if self.input == 'number' and not self.mask.startswith('-'):
                self.width += 1
        if self.width is None:
            self.width = {'number': 12, 'date': 12, 'time': 10,
                          'datetime-local': 16, 'boolean': 6, 'checkbox': 6,
                          'image': 12}.get(self.input, 18)
        if self.input == 'number' and self.align == 'left':
            self.align = 'right'

    @property
    def display_label(self) -> str:
        return self.label or _auto_label(self.name)

    @property
    def width_ch(self) -> int:
        return self.width


def get_field(fields: list[Field], name: str) -> Optional[Field]:
    for f in fields:
        if f.name == name:
            return f
    return None


# ── Construção do Field a partir de uma config ──────────────────────────────
def build_field_config(name: str, cfg: dict) -> dict:
    field_type = cfg.get('type', 'TEXT')
    defaults = FIELD_TYPES.get(field_type, {})
    if 'type' not in cfg:
        defaults = {k: v for k, v in defaults.items() if k != 'required'}
    props = {**defaults, **cfg, 'name': name}
    props.pop('type', None)

    if 'label' not in props:
        props['label'] = _auto_label(name)

    # `query` fica como config crua (entrada para relacionamentos/FK).
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
        props['mask'] = '9999' if d == 0 else f'9999.{"9" * d}'

    return props


def build_field(name: str, cfg: dict) -> Field:
    """Instancia um `Field` a partir de uma config de entrada."""
    return Field(**build_field_config(name, cfg))


class FieldConfigError(ValueError):
    """Config de `Entity`/`Schema` inválida (chave desconhecida)."""


_FIELD_KEYS = (
    frozenset(f.name for f in dc_fields(Field)) | {'type', 'list'} - {'name'}
)


def validate_field_config(cfg: dict, where: str, campo: str) -> None:
    """Valida as chaves de um campo contra as props do dataclass `Field`.

    Fonte da verdade = o dataclass `Field` (adicionar/mudar uma prop o reflete
    aqui automaticamente, sem sync manual). `name` (a própria chave do campo) é
    excluído; `type`/`list` são chaves de CONFIG consumidas pelo
    `build_field_config` (não viram atributo do `Field`). Schema aceita o mesmo
    conjunto que Entity (override completo).
    """
    if not isinstance(cfg, dict):
        raise FieldConfigError(
            f"Config de '{campo}' em {where} deve ser um dict, veio {type(cfg).__name__}"
        )
    for k in cfg:
        if k not in _FIELD_KEYS:
            raise FieldConfigError(
                f"Chave '{k}' não é válida em {where} ('{campo}'). "
                f"Chaves aceitas: {sorted(_FIELD_KEYS)}"
            )


# ── Resolução Entity (model) / Schema (rota) ────────────────────────────────
def _entidade_fields(ent_cfg) -> dict:
    """Campos de uma entrada de `Entity`, ignorando chaves reservadas `__*`."""
    return {k: v for k, v in (ent_cfg or {}).items() if not k.startswith('__')}


def entity_fields(model_cls) -> dict:
    """Lê a definição `Entity` do arquivo do model → {campo: cfg} ({} se ausente).

    Suporta formato direto `{'campo': cfg}` ou aninhado `{'ModelName': {'campo': cfg}}`.
    """
    if model_cls is None:
        return {}
    mod = importlib.import_module(model_cls.__module__)
    ent = getattr(mod, 'Entity', None)
    if not isinstance(ent, dict):
        return {}
    if model_cls.__name__ in ent:
        ent = ent[model_cls.__name__]
    elif ent and any(isinstance(v, dict) for v in ent.values()):
        first_val = next(iter(ent.values()))
        if isinstance(first_val, dict) and not any(k in _FIELD_KEYS for k in first_val):
            ent = first_val
    return _entidade_fields(ent)


def schema_for_module(module_name: str) -> dict:
    """Lê a variável `Schema` de um módulo de rota ({} se ausente/inválida)."""
    if not module_name:
        return {}
    try:
        mod = importlib.import_module(module_name)
    except ImportError:
        return {}
    schema = getattr(mod, 'Schema', None)
    return schema if isinstance(schema, dict) else {}


def resolve_schema_entity(schema: dict, model_cls, entity_name: str) -> dict:
    """Resolve os campos de uma entidade = merge(Entity do model, Schema).

    `schema` = dict `Schema` da rota (mapa por entidade).
    `model_cls` = classe do model (base). `entity_name` = chave da entidade.
    O override do `Schema` (delta) vence o `Entity` do model (base).
    """
    base = entity_fields(model_cls)
    delta = (schema or {}).get(entity_name, {}) or {}
    out = {}
    for n in set(base) | set(delta):
        b = base.get(n, {}) or {}
        d = delta.get(n, {}) or {}
        out[n] = {**b, **d}
    return out


def _resolve_fieldset(fieldset, extra=None):
    """Converte dict de campos `{nome: cfg}` em lista de `Field`.
    `extra` = {nome: override} (contextual)."""
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


# ── Leitura declarativa de módulo de rota (Page/Schema/Form/List) ───────────
def module_page(mod) -> dict:
    """Lê o dict `Page` de um módulo de rota ({} se ausente/não-dict)."""
    p = getattr(mod, 'Page', None)
    return p if isinstance(p, dict) else {}


def page_props(page: dict) -> dict:
    return (page.get('props') or {}) if isinstance(page, dict) else {}


def page_list_cfg(page: dict) -> dict:
    """Config do `list` de um Page (props.list ou aba type='List')."""
    props = page_props(page)
    lc = props.get('list')
    if isinstance(lc, dict):
        return lc
    tabs = props.get('tabs') or {}
    for cfg in tabs.values():
        if isinstance(cfg, dict) and cfg.get('type') == 'List':
            return {k: v for k, v in cfg.items() if k != 'type'}
    return {}


def page_form_cfg(page: dict) -> dict:
    """Config do `form` de um Page (retorna {} se ausente)."""
    props = page_props(page)
    fc = props.get('form')
    return fc if isinstance(fc, dict) else {}


def page_entity_name(page: dict, default: str = '') -> str:
    """Nome da entidade principal declarada num Page (via list/form fields)."""
    lc = page_list_cfg(page)
    fc = page_form_cfg(page)
    for cfg in (lc, fc):
        f = cfg.get('fields')
        if isinstance(f, str):
            return f
        if isinstance(f, list):
            for item in f:
                if isinstance(item, str):
                    return item.split('.', 1)[0]
    return default


def resolve_entity_fields(schema: dict, model_cls, entity_name: str) -> dict:
    """Resolve os campos de uma entidade (merge Entity(model) ∪ Schema) já
    validando as chaves de cada config contra os conjuntos aceitos.
    Preserva a ordem original definida no model (Entity).
    """
    base = entity_fields(model_cls)
    delta = (schema or {}).get(entity_name, {}) or {}
    out = {}
    # Primeiro adiciona todos da base na ordem exata em que foram definidos
    for n in base:
        b = base.get(n, {}) or {}
        d = delta.get(n, {}) or {}
        merged = {**b, **d}
        if b:
            validate_field_config(b, 'Entity', n)
        if d:
            validate_field_config(d, 'Schema', n)
        out[n] = merged
    # Depois adiciona eventuais extras que só venham no delta (Schema)
    for n in delta:
        if n not in out:
            d = delta.get(n, {}) or {}
            validate_field_config(d, 'Schema', n)
            out[n] = d
    return out


# ── Registro de models (referências/FK) ─────────────────────────────────────
MODEL_MAP: dict[str, type] = {}


def register_model(name: str, model_class: type) -> None:
    MODEL_MAP[name] = model_class


def fk_target_model(model, field_name):
    """Model alvo de um campo FK `field_name` no `model`.

    Usa a relationship cuja coluna local é `field_name` (senão uma relationship
    com o mesmo nome), ou a coluna FK (via `foreign_keys` → tabela registrada).
    Retorna a classe do model alvo, ou `None` se o campo não for FK.
    """
    if model is None or field_name is None:
        return None
    mapper = getattr(model, '__mapper__', None)
    if mapper is not None:
        for rel in mapper.relationships.values():
            cols = getattr(rel, 'local_columns', None)
            if cols and any(c.name == field_name for c in cols):
                return rel.mapper.class_
        rel = mapper.relationships.get(field_name)
        if rel is not None:
            return rel.mapper.class_
    try:
        col = model.__table__.columns.get(field_name)
    except Exception:
        return None
    if col is None or not col.foreign_keys:
        return None
    for fk in col.foreign_keys:
        tbl_name = fk.column.table.name
        for cls in MODEL_MAP.values():
            if getattr(cls, '__tablename__', None) == tbl_name:
                return cls
    return None
