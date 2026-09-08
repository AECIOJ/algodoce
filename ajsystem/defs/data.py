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

Esta camada NÃO importa `Query` (a espec de busca/FK entra depois, quando uma
página precisar).
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
    'ID':        {'input': 'number', 'pos_form': 0, 'label': '#'},
    'DK':        {'input': 'number', 'pos_form': 0, 'pos_filter': 0},
    'DATA':      {'input': 'date'},
    'DATA_HORA': {'input': 'datetime-local'},
    'HORA':      {'input': 'time'},
    'BOOL':      {'input': 'boolean'},
    'FONE':      {'input': 'text', 'mask': '(99) 99999-9999', 'digits_only': True},
    'CPF':       {'input': 'text', 'mask': '999.999.999-99', 'digits_only': True, 'validate': 'cpf'},
    'CNPJ':      {'input': 'text', 'mask': '99.999.999/9999-99', 'digits_only': True, 'validate': 'cnpj'},
    'FK':        {'input': 'select'},
    'LIST':      {'input': 'select'},
    'MULT10':    {'input': 'multi', 'pos_filter': 0},
    'IMAGE':     {'input': 'image', 'pos_filter': 0, 'required': False},
}

# `required` é sempre opt-in: declarado na Entity/Schema via 'required': True.


_DOW_PT = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom']
_MES_PT = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun',
           'jul', 'ago', 'set', 'out', 'nov', 'dez']
_DATE_TOKENS_RE = re.compile(r'ddd|mmm|aaaa|yyyy|aa|yy|dd|mm')


def has_date_tokens(mask):
    """Diz se a máscara tem tokens de data (`dd`/`mm`/`mmm`/`aa`/`yy`/`aaaa`/`yyyy`/`ddd`)."""
    return bool(mask) and _DATE_TOKENS_RE.search(str(mask)) is not None


def fmt_mask(value, mask):
    """Aplica `mask` a `value`. Tolerante: extrai dígitos antes de formatar.

    Com tokens de data e valor data/hora: `dd`/`mm`/`aaaa` (ou `yyyy`)/
    `aa` (ou `yy`) do dia/mês/ano, `ddd` dia da semana e `mmm` mês abreviado
    (PT, sem locale); `9`s preenchidos dos dígitos DDMMYYYY; literais passam
    direto. Sem tokens (ou valor sem data): caminho original de dígitos.
    """
    if value is None:
        return ''
    if has_date_tokens(mask) and hasattr(value, 'strftime') and hasattr(value, 'year'):
        return _fmt_mask_data(value, mask)
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


def _fmt_mask_data(value, mask):
    """Formata data/hora pela máscara com tokens (ver `fmt_mask`)."""
    y, m, d = value.year, value.month, value.day
    rep = {
        'aaaa': f'{y:04d}',
        'yyyy': f'{y:04d}',
        'aa': f'{y % 100:02d}',
        'yy': f'{y % 100:02d}',
        'mmm': _MES_PT[m - 1],
        'mm': f'{m:02d}',
        'ddd': _DOW_PT[value.weekday()],
        'dd': f'{d:02d}',
    }
    digits = f'{d:02d}{m:02d}{y:04d}'
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
    text = ''.join(out)
    for tok in ('aaaa', 'yyyy', 'aa', 'yy', 'mmm', 'mm', 'ddd', 'dd'):
        if tok in text:
            text = text.replace(tok, rep[tok])
    return text


def _auto_label(name: str) -> str:
    if name.endswith('_id'):
        return name[:-3].capitalize()
    return ' '.join(w.capitalize() for w in name.split('_'))


def resolve_max_width(value):
    """`max_width` de list/form: `int` → `<n>ch`; string é CSS pronto.

    `None` (prop ausente) → `None` (o template aplica o default). `int` deve
    ser positivo; `bool` não é int aceitável. Qualquer outro tipo é erro de
    config (fail-fast).
    """
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("max_width deve ser int (largura em ch) ou string CSS")
    if isinstance(value, int):
        if value <= 0:
            raise ValueError(f"max_width deve ser positivo (recebido {value})")
        return f"{value}ch"
    if isinstance(value, str):
        return value
    raise ValueError("max_width deve ser int (largura em ch) ou string CSS")


# ── Dataclass Field (runtime resolvido) ──────────────────────────────────────
@dataclass
class Query:
    """Especificação declarativa de consulta (usada em List e Report)."""
    columns: Union[str, list, dict, None] = None
    join: Optional[Union[str, list, dict]] = None
    when: Optional[Union[str, dict, Callable]] = None
    groups: Optional[Union[str, list[str]]] = None
    order: Optional[Union[str, list[str]]] = None


@dataclass
class Table:
    """Especificação de tabela editável (Master-Detail) em sessões de formulário."""
    columns: Union[str, list, dict, None] = None
    order: Optional[Union[str, list[str]]] = None


@dataclass
class Lookup:
    """Complemento de um campo para escolha/exibição por busca. Define COMO
    escolher e exibir um registro vinculado (FK).

    - `fields`:  campo(s) a listar ao escolher. `1` → `<select>`; `>1` → `<modal>`.
                 Default: `[display]`.
    - `display`: campo a exibir (listagem/readonly e no select). Default: primeiro
                 campo após `id` da entidade alvo (senão o primeiro campo).
    - `value`:   campo a retornar e gravar no registro. Default: `'id'`.
    - `when`:    condição para listar nas opções de escolha (dict ou string SQL).
    - `query`:   nome de uma busca declarada na rota (ex.: `'PREVISOES'`) — em vez
                 de `<select>`, renderiza display + hidden + botão externo que abre
                 modal de busca alimentado pelo endpoint do motor.
    """
    fields: Optional[Union[str, list]] = None
    display: Optional[str] = None
    value: Optional[str] = None
    when: Optional[Union[str, dict, Callable]] = None
    query: Optional[str] = None


@dataclass
class Session:
    """Especificação de uma sessão filha (bloco) em um Formulário (`Form`).
    
    Se `template` for fornecido, ele é renderizado diretamente e as demais
    propriedades são ignoradas. Caso contrário, contém obrigatoriamente
    `query` (somente leitura) OU `table` (editável).
    """
    template: Optional[str] = None
    fields: Union[str, list, dict, None] = None
    query: Optional[dict] = None
    table: Optional[Union[dict, Table]] = None

    def __post_init__(self):
        if self.template:
            return
        if self.query is not None and self.table is not None:
            raise ValueError("Sessão: defina 'query' OU 'table', não ambas na mesma sessão.")


@dataclass
class Field:
    name: str
    label: Optional[str] = None
    width: Optional[int] = None
    align: str = 'left'
    input: str = 'text'
    options: Optional[dict] = None
    pos_filter: Optional[int] = None
    mask: Optional[str] = None
    input_name: Optional[str] = None  # nome do input no HTML (default: field.name); o save lê `input_name or name`
    lookup: Any = None         # complemento de escolha/exibição (dict | Lookup | True)
    validate: Optional[Union[str, list, Callable]] = None
    decimals: Optional[int] = None
    min: Optional[Union[int, float]] = None
    max: Optional[Union[int, float]] = None
    step: Optional[Union[int, float]] = None
    currency: Optional[Union[int, str, bool]] = None  # código CURRENCY (0=off); True/'brl' legados = padrão
    percent: bool = False
    required: bool = False
    placeholder: Optional[str] = None
    help: Any = None
    transform: Any = None
    disabled: bool = False
    readonly: bool = False
    hidden: bool = False
    digits_only: bool = False
    pos_form: int = 1
    pos_list: int = 1
    default: Any = None
    rows: int = 1
    on_set: Optional[dict] = None  # efeitos ao setar: {'replaces': {...},
        # 'disables': [...]} (ver README)
    calc: Optional[Union[str, Callable]] = None
    tag: Any = None

    def __post_init__(self):
        if self.pos_filter is True:
            self.pos_filter = 1
        elif self.pos_filter is False:
            self.pos_filter = 0
        if self.pos_filter == 9:
            # filtro fixo: gerenciado pelo motor — fora do corpo, da lista
            # e do painel (a força vence declaração explícita)
            self.pos_form = 0
            self.pos_list = 0
        if self.pos_form is True:
            self.pos_form = 1
        elif self.pos_form is False:
            self.pos_form = 0
        if self.pos_list is True:
            self.pos_list = 1
        elif self.pos_list is False:
            self.pos_list = 0
        if self.tag is not None:
            from ajsystem.defs.tags import parse_tag
            self.tag = parse_tag(self.tag)
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
def module_page(mod) -> "Page":
    """Lê o `Page` de um módulo de rota (dataclass; {} → Page vazio)."""
    from ajsystem.defs.pages import parse_page
    p = getattr(mod, 'Page', None)
    if p is None:
        return parse_page({})
    return parse_page(p)


def module_page_label(page) -> str:
    """`label` do `Page` (ex.: 'Orçamento'). Usado como rótulo do form (id na
    navegação, msgs de inclusão/alteração)."""
    return (page.label or '') if not isinstance(page, dict) else (page.get('label') or '')


def page_props(page) -> dict:
    props = getattr(page, 'props', None)
    if props is not None:
        return props or {}
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


def fk_relation_name(model, field_name):
    """Nome do atributo de relação (`pai`, `cliente`, ...) cuja coluna local é
    `field_name` no `model`. Fallback: nome do campo com `_id` removido."""
    mapper = getattr(model, '__mapper__', None)
    if mapper is not None:
        for key, rel in mapper.relationships.items():
            cols = getattr(rel, 'local_columns', None)
            if cols and any(c.name == field_name for c in cols):
                return key
    if field_name and field_name.endswith('_id'):
        return field_name[:-3]
    return field_name


def _target_first_fields(target_model):
    """Campos tabelados do `target_model` na ordem das colunas (ignorando pk)."""
    keys = []
    try:
        cols = list(target_model.__table__.columns)
    except Exception:
        return keys
    for col in cols:
        if getattr(col, 'name', None) and col.name != 'id':
            keys.append(col.name)
    return keys


def resolve_lookup(field, source_model):
    """Resolve a prop `lookup` de um `Field` numa config com defaults.

    `lookup` pode ser: `True` (usa defaults), dict, ou um objeto `Lookup`.
    O que o motor infere da FK (`fk_target_model`): o model a pesquisar. O que a
    config informa:
      - `display`: campo a exibir (default: primeiro campo após `id`).
      - `value`:   campo a retornar/gravar (default: 'id').
      - `fields`:  campo(s) a listar ao escolher (default: [`display`]).
      - `when`:    condição para listar nas opções de escolha.
      - `replaces`: `replaces` de `on_set` do `Field` (efeitos ao setar).
        Valor str = atributo-fonte do registro (select FK); valor dict =
        mapa por-opção `{valor_opcao: literal}` (p/ LIST); escalar = constante.
    Retorna dict resolvido com `path` (`<relação>.<display>`) ou `None`.
    """
    raw = getattr(field, 'lookup', None)
    if raw is None or raw is False:
        return None
    cfg = {}
    if raw is not True:
        if isinstance(raw, Lookup):
            cfg = {k: v for k, v in vars(raw).items() if v is not None}
        elif isinstance(raw, dict):
            cfg = dict(raw)
    _os = getattr(field, 'on_set', None)
    cfg['replaces'] = _os.get('replaces') if isinstance(_os, dict) else None

    target = fk_target_model(source_model, field.name) if source_model else None
    display = cfg.get('display')
    if not display:
        if target is not None:
            firsts = _target_first_fields(target)
            display = firsts[0] if firsts else 'id'
        else:
            display = 'id'
    value = cfg.get('value', 'id')
    fields = cfg.get('fields')
    if fields is None:
        fields = [display]
    elif isinstance(fields, str):
        fields = [fields]
    relation = (fk_relation_name(source_model, field.name)
                if source_model else field.name)
    return {
        'display': display,
        'fields': fields,
        'value': value,
        'when': cfg.get('when'),
        'replaces': cfg.get('replaces'),
        'query': cfg.get('query'),
        'path': f'{relation}.{display}',
    }


def _when_value(v):
    """Coage valor escalar de `when`: 'true'/'false' → bool; numérico → número."""
    if isinstance(v, str):
        s = v.strip().strip("'\"")
        if s.lower() == 'true':
            return True
        if s.lower() == 'false':
            return False
        try:
            return int(s)
        except (TypeError, ValueError):
            pass
        try:
            return float(s)
        except (TypeError, ValueError):
            pass
        return s
    return v


def _when_in_list(rval):
    """Parseia lista de `IN (...)`: [valores] sem Nones (NULL não casa em IN)."""
    s = (rval or '').strip()
    if s.startswith('(') and s.endswith(')'):
        s = s[1:-1]
    items = []
    for part in s.split(','):
        part = part.strip()
        if not part:
            continue
        v = _when_value(part)
        if v is not None:
            items.append(v)
    return items


def apply_lookup_when(query, target_model, when):
    """Aplica a condição `when` de um lookup a uma query alvo.

    Suporta dict (`{'col': valor}`; `None` → `IS NULL`; lista/tupla/set →
    `IN`, vazia → ignora) ou string SQL simples com `=`, `!=`, `IN`, `NOT IN`,
    `IS NULL`, `IS NOT NULL` unidas por `AND`."""
    if not when:
        return query
    if callable(when):
        raise TypeError("lookup.when deve ser dict ou string, não callable")
    try:
        col = target_model.__table__.columns
    except Exception:
        return query

    conds = []
    if isinstance(when, dict):
        for k, v in when.items():
            try:
                f = col.get(k)
            except Exception:
                f = None
            if f is None:
                continue
            if v is None:
                conds.append(f.is_(None))
            elif isinstance(v, (list, tuple, set, frozenset)):
                vals = [x for x in v if x is not None]
                if vals:
                    conds.append(f.in_(vals))
            else:
                conds.append(f == v)
    elif isinstance(when, str):
        import re as _re
        for m in _re.finditer(r'(\w+)\s*(NOT IN|IN|!=|=|IS NULL|IS NOT NULL)\s*(.*?)(?:\s+AND\s+|$)', when, _re.IGNORECASE):
            name, op, rval = m.group(1), m.group(2).upper(), m.group(3).strip()
            try:
                f = col.get(name)
            except Exception:
                f = None
            if f is None:
                continue
            if op in ('IS NULL', 'IS NOT NULL'):
                conds.append(f.is_(None) if op == 'IS NULL' else f.isnot(None))
            elif op in ('IN', 'NOT IN'):
                vals = _when_in_list(rval)
                if not vals:
                    continue
                conds.append(f.in_(vals) if op == 'IN' else ~f.in_(vals))
            else:
                rval = _when_value(rval)
                if op == '!=':
                    conds.append(f != rval)
                else:
                    conds.append(f == rval)
    for c in conds:
        query = query.filter(c)
    return query
