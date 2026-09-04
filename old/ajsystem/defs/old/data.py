"""DATA — camada declarativa de dados (Field, Entity, Schema).

Reúne o dataclass `Field` (representação resolvida de um campo) e os
resolvedores das variáveis declarativas `Entity` (definição base no model) e
`Schema` (overrides por página na rota).

Vocabulário:
- `model`  → a classe `db.Model` (a tabela).
- `Entity` → variável declarativa no ARQUIVO DO MODEL: definição dos campos
  (type, mask, currency, label, transform, width, options...), servindo aos
  componentes list/form/report.
- `Schema` → variável declarativa na ROTA (a antiga `Entity` da página):
  enumera as entidades usadas + overrides por página (in_list/in_form/label,
  query/options contextuais, etc.). O que vier aqui VENCE o `Entity` do model.
- `Field`  → dataclass interno (resolvido via `build_field_config`); nunca é
  declarado pelo dev.

Regra de merge por campo: `Entity[field] ∪ Schema[entidade][field]`, com o
override da página vencendo. O `Entity` do model é a fonte-base; se o model
não tiver `Entity`, o `Schema`/config da rota vale integral (compat).

Validação (fail-fast): chave de configuração desconhecida no `Entity`/`Schema`
lança `ValueError` claro, evitando typos silenciosos. Novas props entram
somente mediante aprovação (checklist).
"""
import importlib

from app.ajsystem.defs.query import Query
from app.ajsystem.defs.fields import FIELD_TYPES, Field, _auto_label


# ── Conjuntos de chaves aceitas (derivados do checklist aprovado) ────────────
# `Entity` (model) = definição completa p/ list/form/report.
ENTITY_KEYS = {
    'type', 'label', 'width', 'grid', 'align', 'input', 'options', 'list',
    'mask', 'query', 'query_filter', 'validate', 'decimals', 'min', 'max',
    'step', 'masterkey', 'derived', 'currency', 'percent', 'hide_zero', 'link',
    'required', 'placeholder', 'help', 'transform', 'disabled', 'readonly',
    'hidden', 'upload_path', 'digits_only', 'attrs', 'in_form', 'in_list',
    'in_filter', 'default', 'rows', 'on_set', 'on_set_ent', 'on_set_mod',
    'calc', 'code',
}
# `Schema` (rota) = override por página (subset focado em render/contexto).
SCHEMA_KEYS = {
    'label', 'width', 'grid', 'align', 'input', 'options', 'list', 'mask',
    'query', 'validate', 'decimals', 'min', 'max', 'step', 'currency',
    'percent', 'hide_zero', 'required', 'placeholder', 'help', 'transform',
    'disabled', 'readonly', 'hidden', 'attrs', 'in_form', 'in_list',
    'in_filter', 'default', 'on_set', 'on_set_ent', 'on_set_mod', 'calc',
}


class FieldConfigError(ValueError):
    """Erro de configuração de `Entity`/`Schema` (chave desconhecida)."""


def validate_field_config(cfg: dict, keys: set, where: str, campaigne: str) -> None:
    """Valida as chaves de um field contra o conjunto aceito (fail-fast)."""
    for k in cfg:
        if k not in keys:
            raise FieldConfigError(
                f"Chave '{k}' não é válida em {where} ('{campaigne}'). "
                f"Chaves aceitas: {sorted(keys)}"
            )


# ── Resolução de Entity (model) ───────────────────────────────────────────────
def entity_fields(model_cls) -> dict:
    """Lê a definição `Entity` do arquivo do model (variável de módulo).

    Retorna o dict {campo: cfg} — ou {} quando o model não a declara.
    """
    if model_cls is None:
        return {}
    mod = importlib.import_module(model_cls.__module__)
    ent = getattr(mod, 'Entity', None)
    if not isinstance(ent, dict):
        return {}
    return {k: v for k, v in ent.items() if not k.startswith('__')}


# ── Resolução de Schema (rota) ────────────────────────────────────────────────
def schema_for_module(module_name: str) -> dict:
    """Lê a variável `Schema` de um módulo de rota (ou {} — compat)."""
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
    for name in set(base) | set(delta):
        b = base.get(name, {})
        d = delta.get(name, {})
        out[name] = {**b, **d}
    return out


def build_field(name: str, cfg: dict) -> Field:
    """Instancia um `Field` a partir de uma config (defaults por tipo etc.)."""
    merged = build_field_config(name, cfg)
    return Field(**merged)


# Re-exportação: `build_field_config` vive aqui no padrão Entity → Field.
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
        props['query'] = Query(model=mk)

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
        dm = props['decimals']
        if dm == 0:
            props['mask'] = '9999'
        else:
            props['mask'] = f'9999.{"9" * dm}'

    return props


FIELD_DEFAULTS = FIELD_TYPES


__all__ = [
    'Field', 'FieldConfigError',
    'entity_fields', 'schema_for_module', 'resolve_schema_entity',
    'build_field_config', 'build_field', 'validate_field_config',
    'ENTITY_KEYS', 'SCHEMA_KEYS',
]
