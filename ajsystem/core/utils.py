"""Helpers genéricos de formatação/utilidade do framework.

Reutilizados por templates (filtros Jinja) e pelo motor de listagem/formulário.
Não dependem de modelos nem da aplicação host.
"""
import re
import unicodedata
from datetime import datetime, timedelta

from flask import Blueprint
from flask_login import login_required

# Formatação/parse de máscara, número, moeda, data, transforms e validadores
# centralizados em `core/formats.py` (ver lá). Re-export para compat.
from ajsystem.core.formats import (  # noqa: F401
    parse_brl, fmt_id, fmt_brl, _fmt_number, normalize_currency, currency_symbol,
    fmt_money, fmt_percent, fmt_num, fmt_zero, fmt_date, fmt_zero_int,
    fmt_datetime, _title_case, apply_transform,
    mask_strip, fmt_mask_cmd, parse_mask_commands,
)
from ajsystem.defs.constants import CONNECTORS, CURRENCY, DEFAULT_CURRENCY  # noqa: F401


def as_options(*itens, slug=True):
    """Dict de opções {valor: rótulo} para fields `LIST` (varargs, sem `[]`).

    Cada item é um rótulo — a chave deriva do rótulo via `normalizar_slug`
    com espaço convertido em `_` (ex.: 'Chá de Bebê' → 'cha_de_bebe') — ou um
    par `(chave, rótulo)` quando a chave não deriva do rótulo.
    `slug=False` usa o próprio rótulo como chave (identidade).
    """
    opts = {}
    for item in itens:
        if isinstance(item, (tuple, list)):
            key, label = item
        else:
            label = item
            key = label if not slug else re.sub(r'\s+', '_', normalizar_slug(label))
        opts[key] = label
    return opts


def deep_attr(obj, path):
    if obj is None:
        return None
    for part in path.split('.'):
        if obj is None:
            return None
        try:
            obj = getattr(obj, part)
        except AttributeError:
            try:
                obj = obj[part]
            except (TypeError, KeyError, IndexError):
                return None
    return obj


def field_value(field, item):
    """Valor de um campo para `item`: acesso aninhado pelo nome."""
    return deep_attr(item, getattr(field, 'name', '') or '')


def normalizar_slug(label: str) -> str:
    """Slug de um rótulo/entidade: ASCII, minúsculo e sem espaços nas pontas."""
    s = unicodedata.normalize('NFKD', label or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


def snake_case(name) -> str:
    """`'Event'` → `'event'` (snake_case de um nome de entidade)."""
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name or '').lower()


def is_empty(val):
    """True para `None`, string vazia ou coleção vazia (falso para 0)."""
    if val is None:
        return True
    if isinstance(val, str):
        return val == ''
    if isinstance(val, (list, tuple, dict, set)):
        return len(val) == 0
    return False


def module_blueprint(mod):
    """Primeiro objeto `Blueprint` exposto pelo módulo, ou `None`."""
    for name in dir(mod):
        obj = getattr(mod, name, None)
        if isinstance(obj, Blueprint):
            return obj
    return None


def model_columns(model):
    """Dict de colunas do modelo (pela `__table__`), ou `{}`."""
    table = getattr(model, '__table__', None)
    return getattr(table, 'columns', None) or {}


def fk_column_to(model, target_model):
    """Nome da coluna FK em `model` cujo alvo é `target_model`, ou `None`."""
    mapper = getattr(model, '__mapper__', None)
    if mapper is None or target_model is None:
        return None
    for rel in mapper.relationships.values():
        if getattr(rel, 'mapper', None) is not None and rel.mapper.class_ is target_model:
            for col in getattr(rel, 'local_columns', None) or []:
                return col.name
    return None


def fk_target(model, column_name):
    """Modelo alvo da FK `column_name`, ou `None`."""
    mapper = getattr(model, '__mapper__', None)
    if mapper is None or not column_name:
        return None
    for rel in mapper.relationships.values():
        for col in getattr(rel, 'local_columns', None) or []:
            if col.name == column_name:
                return rel.mapper.class_
    return None


def rel_for_column(model, column_name):
    """Nome da relationship cuja coluna local é `column_name`, ou `None`."""
    mapper = getattr(model, '__mapper__', None)
    if mapper is None or not column_name:
        return None
    for rel in mapper.relationships.values():
        for col in getattr(rel, 'local_columns', None) or []:
            if col.name == column_name:
                return rel.key
    return None


def has_back_rel(model, target):
    """True quando `model` tem relação de volta (uselist ou não) p/ `target`."""
    mapper = getattr(model, '__mapper__', None)
    if mapper is None:
        return False
    for rel in mapper.relationships.values():
        try:
            if rel.mapper.class_ is target:
                return True
        except Exception:
            continue
    return False


def protect_blueprint(bp):
    """Aplica `@login_required` a todas as rotas de um blueprint."""
    @bp.before_request
    @login_required
    def _guard():
        pass


def divide(a, b):
    """Divisão segura: retorna 0 quando `b` é nulo/zero, evitando
    `ZeroDivisionError`."""
    if not b:
        return 0
    try:
        return a / b
    except (TypeError, ValueError):
        return 0


def add_dias(dta, dias):
    """Soma `dias` a uma data/hora, ignorando fuso. Retorna o mesmo tipo:
    `datetime` in → `datetime`, `date` in → `date`. `dias` nulo/0 é tratado
    como 0; `dta` nulo/ausente → `None`."""
    if dta is None:
        return None
    try:
        dias = int(dias or 0)
    except (TypeError, ValueError):
        dias = 0
    ref = dta
    if isinstance(ref, datetime) and ref.tzinfo is not None:
        ref = ref.replace(tzinfo=None)
    return ref + timedelta(days=dias)


def _agg_children(item, child_entity):
    """Iterável de filhos de `item` cujo model é o da entidade `child_entity`.

    Resolve a entidade (ex.: `'PedidoItem'`) para o model via `_resolve_model`
    e devolve o atributo de relationship do pai cujo mapper aponta para ele.
    """
    from sqlalchemy.orm import MANYTOONE
    try:
        from ajsystem.core.list import _resolve_model
        child_model = _resolve_model(child_entity)
    except Exception:
        return None
    mapper = getattr(item.__class__, '__mapper__', None)
    if mapper is None:
        return None
    for name, rel in mapper.relationships.items():
        try:
            if (rel.mapper.class_ == child_model
                    and rel.direction is not MANYTOONE):
                return getattr(item, name, None) or []
        except Exception:
            continue
    return None


_AGG_RE = re.compile(r'^(sum|avg|count|max|min)\(([A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?)?\)$')


def _agg_value(spec, item):
    """Agregação de filhos a partir de `spec['source']` tipo `sum(Entity.field)`.

    Suporta `sum/avg/count/max/min`. `count()` conta os filhos; as demais
    agregam o campo (caminho com `.` resolvido por `deep_attr`). Filtra opcional
    com `spec['when']` (dict de igualdade sobre atributos do filho).
    """
    m = _AGG_RE.match((spec.get('source') or '').strip())
    if m is None:
        return None
    fn, target = m.group(1), m.group(2)
    if target is None:
        # `count()` sem campo → precisa da entidade via `spec['entity']`
        children = _agg_children(item, spec.get('entity')) if spec.get('entity') else None
    else:
        entity, _, field = target.partition('.')
        children = _agg_children(item, entity)
    if children is None:
        return None
    when = spec.get('when') or {}
    vals = []
    for it in children:
        if when and any(deep_attr(it, k) != v for k, v in when.items()):
            continue
        if fn == 'count':
            vals.append(1)
            continue
        v = deep_attr(it, field)
        try:
            vals.append(float(v))
        except (TypeError, ValueError):
            continue
    if fn == 'sum':
        return sum(vals)
    if fn == 'avg':
        return sum(vals) / len(vals) if vals else 0
    if fn == 'count':
        return len(vals)
    if fn == 'max':
        return max(vals) if vals else 0
    if fn == 'min':
        return min(vals) if vals else 0
    return None


def _call_value(spec, item):
    """Chamada única no pai a partir de `spec['source']` (método ou callable)."""
    source = spec.get('source')
    if callable(source):
        return source(item)
    if isinstance(source, str):
        fn = getattr(item, source, None)
        if callable(fn):
            return fn()
    return None


def _spec_value(spec, item):
    """Resolve um dict `calc` (`{'type': 'call'|'agg', ...}`)."""
    if not isinstance(spec, dict):
        return None
    kind = spec.get('type')
    if kind == 'call':
        return _call_value(spec, item)
    if kind == 'agg':
        return _agg_value(spec, item)
    return None


def calc_value(calc, item):
    """Valor de um campo `calc` (virtual, não persistido) para `item`.

    - callable → `calc(item)`;
    - string → expressão aritmética avaliada com namespace restrito aos
      atributos de `item` (mesmo padrão do `_apply_aggs`);
    - dict → `{'type': 'call'}` (método/callable no pai) ou
      `{'type': 'agg', 'source': 'sum(Entity.campo)'}` (agregação de filhos);
    - outro valor (constante) → o próprio valor.
    """
    if isinstance(calc, dict):
        return _spec_value(calc, item)
    if callable(calc):
        return calc(item)
    if not isinstance(calc, str):
        return calc
    names = set(re.findall(r'[A-Za-z_][A-Za-z0-9_]*', calc or ''))
    ns = {n: (getattr(item, n, None) or 0) for n in names}
    ns['divide'] = divide
    try:
        return eval(calc, {'__builtins__': {}}, ns)
    except Exception:
        return None


def item_ref(item, siblings):
    """Identificador curto do registro para cabeçalhos de coluna (tabela
    transposta): usa a(s) coluna(s) da chave primária que variam entre os
    itens irmãos. Ex.: linha filha usa a FK para o pai; item de linha usa o
    próprio `id`. Retorna None quando não há como identificar (item novo/sem
    pk)."""
    if item is None:
        return None
    if isinstance(item, dict):
        return item.get('id')
    try:
        cols = list(item.__table__.primary_key.columns)
    except Exception:
        return getattr(item, 'id', None) or None
    if not cols:
        return getattr(item, 'id', None) or None
    varying = []
    for c in cols:
        vals = {getattr(i, c.name, None) for i in siblings}
        if len(vals) > 1:
            varying.append(c.name)
    names = varying or [c.name for c in cols]
    vals = [getattr(item, n, None) for n in names]
    vals = [v for v in vals if v is not None]
    return '-'.join(str(v) for v in vals) if vals else None


def preco_unit(valor, qtd):
    if not valor:
        return 0
    if not qtd:
        return float(valor)
    return float(valor) / float(qtd)


def query_label(cfg, key):
    """Rótulo padrão de uma Query: `label` explícito ou nome da chave."""
    if cfg is None:
        return _title_case(key) if key else ''
    label = cfg.get('label')
    if label:
        return label
    return _title_case(key) if key else ''


def list_table(valores: dict):
    """Cria uma CTE SQL (colunas `codigo`/`descricao`) a partir de um dict
    de valores, para uso em joins de listas de referência."""
    from sqlalchemy import select, union_all, literal
    ctes = [
        select(literal(k).label('codigo'), literal(v).label('descricao'))
        for k, v in valores.items()
    ]
    return union_all(*ctes).cte('list_table')
