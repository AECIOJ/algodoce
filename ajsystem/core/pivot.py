"""PIVOT — executor do `PivotSpec` (`defs/qspec`).

O pivot é outro motor, não uma opção do `qrun`: a query de origem devolve as
linhas em formato **longo** (uma por combinação de eixos) e o executor agrega
em memória, produzindo uma linha por combinação de `lines` e uma coluna por
valor do eixo de `columns` × medida.

Gramática (ver `defs.qspec.PivotSpec`):

    {
      'src': QuerySpec | 'Entidade',
      'lines': ['conta', {'mes': 'data_mes'}],
      'columns': {'field': 'tipo', 'values': [...]},
      'aggs': {'total': {'field': 'valor', 'agg': 'sum'}},
      'filters': {...},          # gramática literal dos filtros
    }

Nomes gerados: ``<alias>__<slug(valor)>``. A coluna é um atributo comum da
linha (o template da listagem lê com `deep_attr`), então nada muda no render.

Semântica:
  - `count` conta valores NÃO nulos (igual a `count(col)` do SQL);
  - `sum/avg/min/max` ignoram `None`; célula sem valores fica `None`;
  - valor `None` no eixo de coluna vira uma coluna própria, rotulada
    ``(vazio)`` e ordenada por último; nos eixos de linha, `None` vem primeiro.
"""
import re
import unicodedata
from dataclasses import dataclass, field as dc_field
from decimal import Decimal

from ajsystem.core.formats import format as _format
from ajsystem.core.qrun import _resolve_column, _resolve_path_model, run_query
from ajsystem.core.utils import deep_attr
from ajsystem.defs.qspec import (
    parse_pivot, parse_select, is_query_dict,
)

_NULL_LABEL = '(vazio)'


# ── metadados do resultado ───────────────────────────────────────────────────
@dataclass
class PivotColumn:
    """Uma coluna gerada: medida × valor do eixo de coluna."""
    name: str
    label: str
    value: object
    agg: str
    field: str
    func: str
    format: str | None = None


@dataclass
class PivotResult:
    rows: list
    columns: list
    lines: list
    spec: object
    column_axis: object = None
    measures: list = dc_field(default_factory=list)


class _PivotRow:
    """Linha leve: atributos dos eixos + colunas geradas (lida por deep_attr)."""


# ── helpers ──────────────────────────────────────────────────────────────────
def _source_name(spec):
    """Entidade de origem do pivot: `src` string ou `src['from']`."""
    src = spec.src
    if isinstance(src, str):
        return src
    if isinstance(src, dict):
        nm = src.get('from')
        if isinstance(nm, (list, tuple)):
            nm = nm[0] if nm else None
        return nm if isinstance(nm, str) else None
    return None


def _slug(value):
    """Slug estável de um valor de eixo -> `[a-z0-9_]` (sem colidir com vazio)."""
    if value is None:
        return 'vazio'
    s = unicodedata.normalize('NFKD', str(value))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^0-9a-zA-Z]+', '_', s).strip('_').lower()
    if not s:
        s = 'vazio'
    if s[0].isdigit():
        s = 'c_' + s
    return s


def _gen_name(alias, value):
    return f'{alias}__{_slug(value)}'


def _value_label(value, fmt=None):
    """Rótulo do valor do eixo de coluna (máscara opcional)."""
    if value is None:
        return _NULL_LABEL
    if fmt:
        try:
            return _format(value, fmt)
        except Exception:
            pass
    return str(value)


def _sort_key(value, *, none_first):
    """Chave de ordenação tolerante a tipos mistos.

    Números (inclusive `Decimal`) ordenam como número; o resto por texto.
    `None` fica primeiro nos eixos de linha (convenção do motor) e por último
    no eixo de coluna.
    """
    if value is None:
        return (0 if none_first else 2, 0, 0)
    if isinstance(value, bool):
        return (1, 1, str(value))
    if isinstance(value, (int, float, Decimal)):
        return (1, 0, value)
    return (1, 1, str(value))


def _sorted_values(values, *, none_first):
    return sorted(values, key=lambda v: _sort_key(v, none_first=none_first))


def _cfg_for(base, field):
    """Cfg de um campo no merged da entidade de origem (path: usa o último nome)."""
    base = base or {}
    cfg = base.get(field)
    if isinstance(cfg, dict):
        return dict(cfg)
    if '.' in field:
        cfg = base.get(field.split('.')[-1])
        if isinstance(cfg, dict):
            return dict(cfg)
    return {}


class _Acc:
    """Acumulador de uma medida numa célula (linha × valor de coluna)."""
    __slots__ = ('n', 'total', 'minimum', 'maximum')

    def __init__(self):
        self.n = 0
        self.total = None
        self.minimum = None
        self.maximum = None

    def add(self, value):
        if value is None:
            return
        self.n += 1
        try:
            self.total = value if self.total is None else self.total + value
            self.minimum = value if self.minimum is None else min(self.minimum, value)
            self.maximum = value if self.maximum is None else max(self.maximum, value)
        except TypeError as exc:
            raise ValueError(f"pivot: valor não agregável {value!r} ({exc})") from exc

    def result(self, func):
        if self.n == 0:
            return None
        if func == 'count':
            return self.n
        if func == 'sum':
            return self.total
        if func == 'avg':
            return self.total / self.n
        if func == 'min':
            return self.minimum
        if func == 'max':
            return self.maximum
        raise ValueError(f"pivot: função de agregação desconhecida '{func}'")


def _validate_field(model, field, keys, dotted, where):
    """Resolve o atributo que a linha assume e valida contra o `src`.

    Com `select` de caminho pontilhado o `qrun` usa `with_entities`, então o
    resultado só tem os nomes do select — usar um campo de fora daria `None`
    silencioso. Fail-fast nomeando o campo e o model.
    """
    name = keys.get(field)
    if name is not None:
        return name
    if not dotted:
        target, leaf = _resolve_path_model(model, field)
        if _resolve_column(target, leaf) is not None:
            return field
    raise ValueError(
        f"pivot: campo '{field}' ({where}) não resolve no model "
        f"'{getattr(model, '__name__', model)}' — inclua-o no select da fonte "
        f"(os campos do select são {sorted(set(keys.values()))})"
    )


# ── executor ─────────────────────────────────────────────────────────────────
def run_pivot(model, spec, entity_cfg=None, extra_where=None,
              extra_conditions=None):
    """Executa `spec` (PivotSpec/dict) sobre `model` e devolve `PivotResult`.

    `entity_cfg` é a cfg flat da entidade de origem (cast/apresentação);
    `extra_where` entra como filtro na gramática literal e `extra_conditions`
    são condições SQLAlchemy já compiladas (painel da listagem/relatório).
    """
    ps = parse_pivot(spec)
    name = _source_name(ps)
    if not name:
        raise ValueError("pivot: 'src' precisa de uma entidade (str ou 'from')")
    if model is None:
        from ajsystem.core.list import _resolve_model
        model = _resolve_model(name)
    if model is None:
        raise ValueError(f"pivot: model da entidade '{name}' não registrado")

    src = ps.src if isinstance(ps.src, dict) else {'from': name}
    if not isinstance(src, dict):
        raise TypeError(f"pivot: 'src' deve ser dict ou entidade, veio {type(ps.src).__name__}")
    if is_query_dict(src) and src.get('from') is None:
        raise ValueError("pivot: 'src' query exige 'from'")

    entries = parse_select(src.get('select'))
    keys = {}
    for e in entries:
        keys.setdefault(e.name, e.name)
        if e.field:
            keys.setdefault(e.field, e.name)
    dotted = any('.' in (e.field or '') for e in entries)

    line_attrs = [
        (ax, _validate_field(model, ax.field, keys, dotted, 'lines'))
        for ax in ps.line_axes
    ]
    col_axis = ps.column_axis
    col_attr = _validate_field(model, col_axis.field, keys, dotted, 'columns')
    measures = [
        (alias, field, func, _validate_field(model, field, keys, dotted, f"aggs '{alias}'"))
        for alias, field, func in ps.measures
    ]

    # O filtro da fonte entra ANTES dos OVERs; filtros do pivot e o filtro
    # externo (painel/relatório) são AND na gramática compartilhada.
    extra = [w for w in (ps.filters, extra_where) if w]
    long_rows = run_query(
        model, src, entity_cfg=entity_cfg,
        extra_where=extra or None, extra_conditions=extra_conditions,
    )

    # Agrega numa passada: grupos[linha][valor_coluna][alias] = _Acc.
    groups = {}
    seen_cols = {}
    for row in long_rows or ():
        line_key = tuple(deep_attr(row, attr) for _, attr in line_attrs)
        col_value = deep_attr(row, col_attr)
        if isinstance(col_value, (list, tuple, set, dict)):
            raise ValueError(
                f"pivot: valor do eixo '{col_axis.field}' não é escalar: "
                f"{col_value!r}")
        for line_value in line_key:
            if isinstance(line_value, (list, tuple, set, dict)):
                raise ValueError(
                    f"pivot: valor de eixo de linha não é escalar: {line_value!r}")
        seen_cols[col_value] = True
        cell = groups.setdefault(line_key, {}).setdefault(col_value, {})
        for alias, field, func, attr in measures:
            acc = cell.get(alias)
            if acc is None:
                acc = cell[alias] = _Acc()
            acc.add(deep_attr(row, attr))

    # Eixo de coluna: ordem declarada (mesmo ausente no recorte) ou descoberta.
    if col_axis.values is not None:
        col_values = list(col_axis.values)
    else:
        col_values = _sorted_values(list(seen_cols), none_first=False)

    # Produto medidas × valores, na ordem declarada, sem colisão de nome.
    columns = []
    used = {ax.name for ax, _ in line_attrs}
    multi = len(measures) > 1
    for alias, field, func, _attr in measures:
        for value in col_values:
            col_name = _gen_name(alias, value)
            if col_name in used:
                raise ValueError(
                    f"pivot: nome gerado '{col_name}' colide (medida '{alias}', "
                    f"valor {value!r})")
            used.add(col_name)
            label = _value_label(value, col_axis.format)
            if multi:
                label = f'{alias} · {label}'
            columns.append(PivotColumn(
                name=col_name, label=label, value=value, agg=alias,
                field=field, func=func, format=col_axis.format,
            ))

    # Uma linha por combinação de eixos, ordenada como o motor (None primeiro).
    rows = []
    for line_key in _sorted_values(list(groups), none_first=True):
        obj = _PivotRow()
        for (ax, _attr), value in zip(line_attrs, line_key):
            setattr(obj, ax.name, value)
        cells = groups[line_key]
        for col in columns:
            acc = cells.get(col.value, {}).get(col.agg)
            setattr(obj, col.name, acc.result(col.func) if acc is not None else None)
        rows.append(obj)

    return PivotResult(
        rows=rows, columns=columns,
        lines=[ax for ax, _ in line_attrs], spec=ps,
        column_axis=col_axis, measures=list(measures),
    )


def pivot_layer(result, base_merged):
    """Camada de apresentação do pivot — `{nome: cfg}` no formato da entidade.

    Análoga a `query_select_layer`: os eixos de linha herdam a cfg da entidade
    de origem (quando existir) e as colunas geradas herdam a cfg do **campo
    medido** (tipo/máscara/decimais), com `label`/`align` do pivot.
    """
    layer = {}
    for ax in result.lines:
        cfg = _cfg_for(base_merged, ax.field)
        for k in ('label', 'width', 'align'):
            v = getattr(ax, k, None)
            if v is not None:
                cfg[k] = v
        if not cfg.get('label'):
            cfg['label'] = ax.label or ax.name
        layer[ax.name] = cfg

    for col in result.columns:
        base = _cfg_for(base_merged, col.field)
        cfg = dict(base)
        cfg['label'] = col.label
        cfg['align'] = 'right'
        if col.func == 'count':
            # contagem é inteira: máscara/decimais do campo medido não valem
            cfg['type'] = 'INT'
            cfg.pop('mask', None)
            cfg.pop('decimals', None)
        elif col.func in ('sum', 'avg'):
            if cfg.get('type') not in ('NUM', 'INT'):
                cfg['type'] = 'NUM'
        elif not cfg.get('type'):
            cfg['type'] = 'NUM'
        layer[col.name] = cfg
    return layer
