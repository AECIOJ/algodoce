"""
ENTITIES — Dataclasses e construção de configuração de dados.

Camada de dados do framework: `Entity`, `Field`, `Query`, `MODEL_MAP` e os
helpers de resolução/construção de campos. Não depende de renderização
(`list`), formulário (`form`) nem relatórios (`report`).

Dependências: apenas as definições `config.filters`/`config.fields` + `utils`.
"""
import importlib
from dataclasses import dataclass, field
from typing import Any, Optional, Callable, Union

from app.ajsystem.defs.fields import FIELD_TYPES
from app.ajsystem.core.utils import _title_case


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
    derived: Optional[dict] = None
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


def _auto_label(name: str) -> str:
    if name.endswith('_id'):
        return name[:-3].capitalize()
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


def get_field(fields: list[Field], name: str) -> Optional[Field]:
    for f in fields:
        if f.name == name:
            return f
    return None


@dataclass
class Entity:
    """Representação runtime de uma entrada do dict `Entity` de um módulo."""

    name: str
    fields: list[Field] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    module_name: str = ''

    def get(self, name: str) -> Optional[Field]:
        return get_field(self.fields, name)

    @property
    def field_names(self) -> list[str]:
        return [f.name for f in self.fields]


def build_entity(name: str, cfg: dict, module_name: str = '') -> Entity:
    """Constrói um `Entity` a partir de uma entrada do dict `Entity` do módulo.

    `cfg` = {field_name: {field_cfg}, '__meta__': {...}, ...}. Chaves `__*__`
    viram `Entity.meta` (com os underscores removidos).
    """
    ent_cfg = cfg or {}
    meta = {}
    if isinstance(ent_cfg, dict):
        for k, v in ent_cfg.items():
            if k.startswith('__'):
                meta[k.strip('_')] = v
    fields = [Field(**build_field_config(n, c))
              for n, c in _entidade_fields(ent_cfg).items()]
    return Entity(name=name, fields=fields, meta=meta, module_name=module_name)


def get_entity(name: str, module_name: str) -> Optional[Entity]:
    """Resolve um `Entity` (com campos prontos) do dict `Entity` de um módulo."""
    mod = importlib.import_module(module_name)
    ent_cfg = getattr(mod, 'Entity', {}).get(name)
    if ent_cfg is None:
        return None
    return build_entity(name, ent_cfg, module_name)
