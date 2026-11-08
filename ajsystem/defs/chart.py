"""Declaração de gráficos como saída do `ReportBody`.

Espelha `table`: o gráfico é declarado dentro do próprio report
(`body.chart`) e reusa `source`, `filter`, `titles`, `variants` e `syn`
do report. Não há `source`/`label` próprios do chart.

Camadas:
  - `parse_chart`     → dict puro da declaração → `Chart` tipado;
  - `normalize_chart` → seleciona a variante/sintético ativos;
  - `ChartDataset`    → saída neutra consumida pelos renderers.
"""
from dataclasses import dataclass, field
from typing import Any, Optional

_CHART_TYPES = ('col', 'bar', 'line', 'area', 'pie', 'donut', 'scatter')
_AGG_TYPES = ('sum', 'avg', 'min', 'max', 'count')
_AXIS_TYPES = ('y', 'y2')
_BUCKETS = ('day', 'month', 'year')
_ORDERS = ('asc', 'desc', 'decl')
_LEGEND_POS = ('top', 'bottom', 'left', 'right', 'none')


def _is_variant_key(key):
    return isinstance(key, int) or (isinstance(key, str) and key.isdigit())


def _variant_key(key):
    """Chaves de variante normalizadas: 0 e '0' são o mesmo nível."""
    return str(key)


@dataclass
class ChartField:
    """Props de um campo individual (categoria ou valor)."""
    agg: str = 'sum'                  # sum|avg|min|max|count
    color: Optional[str] = None       # cor do campo
    axis: str = 'y'                   # y | y2
    format: Optional[str] = None      # máscara de exibição (não afeta o dado)
    bucket: Optional[str] = None      # day|month|year
    order: Optional[str] = None       # asc|desc|decl
    limit: Optional[int] = None       # top N
    variants: Optional[list] = None   # níveis de variante em que o campo entra
    syn: Optional[bool] = None        # False = omite no sintético

    def __post_init__(self):
        if self.agg not in _AGG_TYPES:
            raise ValueError(
                f"chart: agg {self.agg!r} inválido — use {', '.join(_AGG_TYPES)}")
        if self.axis not in _AXIS_TYPES:
            raise ValueError(
                f"chart: axis {self.axis!r} inválido — use y ou y2")
        if self.bucket is not None and self.bucket not in _BUCKETS:
            raise ValueError(
                f"chart: bucket {self.bucket!r} inválido — use "
                f"{', '.join(_BUCKETS)}")
        if self.order is not None and self.order not in _ORDERS:
            raise ValueError(
                f"chart: order {self.order!r} inválido — use "
                f"{', '.join(_ORDERS)}")


@dataclass
class ChartLabel:
    """Rótulos de eixo e dados do gráfico."""
    cat: Optional[str] = None       # rótulo do eixo X
    value: Optional[str] = None     # rótulo do eixo Y (resolvido pelo motor se omitido)
    data: bool = False              # rótulo sobre barras/pontos
    limit: bool | str | None = None # texto explicativo do limite (True = automático)


@dataclass
class ChartOptions:
    """Opções gerais de renderização (não pertencem aos dados)."""
    horizontal: bool = False
    legend: str = 'bottom'          # top|bottom|left|right|none
    tooltip: bool = True
    grid: bool = True
    palette: Optional[str] = None
    height: int = 320
    responsive: bool = True

    def __post_init__(self):
        if self.legend not in _LEGEND_POS:
            raise ValueError(
                f"chart.options.legend {self.legend!r} inválido — use "
                f"{', '.join(_LEGEND_POS)}")


@dataclass
class Chart:
    """Declaração principal (parseada de `ReportBody.chart`).

    Sem `source`/`label`/`filter`: vêm do `Report`.
    """
    title: Optional[str] = None   # título do gráfico (exibido acima do plot)
    type: str = 'col'                        # col=colunas verticais, bar=barras horizontais
    cat: dict = field(default_factory=dict)  # {field: ChartField}
    value: dict = field(default_factory=dict)  # {field: ChartField}
    stack: dict = field(default_factory=dict)  # {grupo: [fields]}
    label: ChartLabel = field(default_factory=ChartLabel)
    options: ChartOptions = field(default_factory=ChartOptions)
    limit: Optional[int] = None  # top N (após ordenação)
    legend: str = 'bottom'       # top|bottom|left|right|none

    def __post_init__(self):
        if self.type not in _CHART_TYPES:
            raise ValueError(
                f"chart: type {self.type!r} inválido — use "
                f"{', '.join(_CHART_TYPES)}")
        if self.legend not in _LEGEND_POS:
            raise ValueError(
                f"chart.legend {self.legend!r} inválido — use "
                f"{', '.join(_LEGEND_POS)}")
        seen = {}
        for group, fields in (self.stack or {}).items():
            if not isinstance(fields, (list, tuple)):
                raise TypeError(
                    f"chart.stack[{group!r}]: deve ser lista de campos")
            for name in fields:
                if name not in self.value:
                    raise ValueError(
                        f"chart.stack[{group!r}]: campo {name!r} não existe "
                        f"em 'value'")
                if name in seen:
                    raise ValueError(
                        f"chart.stack: campo {name!r} aparece nos grupos "
                        f"{seen[name]!r} e {group!r}")
                seen[name] = group


@dataclass
class ChartDataset:
    """Saída neutra do `resolve_chart` — não conhece opções de lib."""
    labels: list = field(default_factory=list)
    series: list = field(default_factory=list)
    meta: dict = field(default_factory=dict)


def _parse_fields(fields, label=''):
    if fields is None:
        return {}
    if not isinstance(fields, dict):
        raise TypeError(f"chart{label}: campos devem ser dict de campos")
    out = {}
    for name, cfg in fields.items():
        if isinstance(cfg, ChartField):
            out[name] = cfg
        elif cfg is None:
            out[name] = ChartField()
        elif isinstance(cfg, dict):
            try:
                out[name] = ChartField(**cfg)
            except TypeError as e:
                raise TypeError(
                    f"chart{label}[{name!r}]: prop inválida — {e}") from e
        else:
            raise TypeError(
                f"chart{label}[{name!r}]: deve ser dict ou ChartField")
    return out


def _parse_label(spec):
    if spec is None:
        return ChartLabel()
    if isinstance(spec, ChartLabel):
        return spec
    if isinstance(spec, dict):
        try:
            return ChartLabel(**spec)
        except TypeError as e:
            raise TypeError(f"chart.label: prop inválida — {e}") from e
    raise TypeError("chart.label deve ser dict ou ChartLabel")


def _apply_filter_fields(active, variant=None, syn=False):
    """Aplica `variants`/`syn` apenas dentro de `cat` e `value`.

    Todas as demais props de nível raiz (`type`, `label`, `options`,
    `limit`, `stack`) são preservadas intactas.
    """
    if not isinstance(active, dict):
        return {}
    out = dict(active)
    for key in ('cat', 'value'):
        fields = out.get(key)
        if not isinstance(fields, dict):
            continue
        kept = {}
        for name, cfg in fields.items():
            cfg = dict(cfg or {})
            clean = {k: v for k, v in cfg.items()
                     if k not in ('syn', 'variants')}
            vs = cfg.get('variants')
            if vs is not None:
                levels = {_variant_key(v) for v in vs}
                if variant is None or _variant_key(variant) not in levels:
                    continue
            if syn and cfg.get('syn') is False:
                continue
            kept[name] = clean
        out[key] = kept
    return out


def normalize_chart(chart, variant=None, syn=False, label=''):
    """Resolve a declaração `chart` para o layout ativo.

    Aceita:
      - layout único na raiz (`type`/`cat`/`value`/`stack`/`label`/`options`
        /`limit`);
      - variantes por chave numérica (`{'0': {...}, '1': {...}}`), com
        `syn` opcional dentro de cada variante.
    """
    if not isinstance(chart, dict) or not chart:
        return None

    has_variants = any(_is_variant_key(k) for k in chart)
    if has_variants:
        if any(k in ('type', 'cat', 'value', 'stack', 'label', 'options',
                     'limit', 'syn') for k in chart):
            raise ValueError(
                f"chart '{label}': não pode misturar variantes com "
                f"type/cat/value/stack/label/options/limit/syn na raiz")
        sel = variant
        if sel is None:
            sel = min((_variant_key(k) for k in chart if _is_variant_key(k)),
                      key=lambda s: int(s))
        sel = _variant_key(sel)
        if sel not in {_variant_key(k) for k in chart}:
            raise ValueError(
                f"chart '{label}': variante {variant!r} não declarada")
        level = chart[next(k for k in chart if _variant_key(k) == sel)]
        if not isinstance(level, dict):
            raise ValueError(
                f"chart '{label}': variante {sel!r} deve ser dict")
        if syn:
            active = level.get('syn')
            if active is None:
                raise ValueError(
                    f"chart '{label}': variante {sel!r} não declara 'syn'")
        else:
            active = {k: v for k, v in level.items() if k != 'syn'}
        return _apply_filter_fields(active, variant=sel, syn=syn)

    if syn:
        active = chart.get('syn')
        if active is None:
            raise ValueError(
                f"chart '{label}': sintético pedido, mas chart não declara 'syn'")
        return _apply_filter_fields(active, variant=variant, syn=True)

    active = {k: v for k, v in chart.items() if k != 'syn'}
    return _apply_filter_fields(active, variant=variant, syn=False)


def chart_has_syn(chart, variant=None):
    """O layout ativo do chart declara `syn`?

    Sem variante selecionada, devolve True se QUALQUER variante declara `syn`
    (o checkbox da tela precisa aparecer antes da escolha).
    """
    if not isinstance(chart, dict) or not chart:
        return False
    has_variants = any(_is_variant_key(k) for k in chart)
    if has_variants:
        if variant is None:
            return any(isinstance(v, dict) and 'syn' in v
                       for k, v in chart.items() if _is_variant_key(k))
        sel = _variant_key(variant)
        key = next((k for k in chart if _variant_key(k) == sel), None)
        level = chart.get(key) if key is not None else None
        return isinstance(level, dict) and 'syn' in level
    return 'syn' in chart


def parse_chart(spec):
    """dict | Chart → Chart (idempotente)."""
    if isinstance(spec, Chart):
        return spec
    if not isinstance(spec, dict):
        raise TypeError(
            f"chart deve ser dict ou Chart, recebido {type(spec).__name__}: "
            f"{spec!r}")
    options = spec.get('options') or {}
    if isinstance(options, dict):
        try:
            options = ChartOptions(**options)
        except TypeError as e:
            raise TypeError(f"chart.options: prop inválida — {e}") from e
    elif not isinstance(options, ChartOptions):
        raise TypeError("chart.options deve ser dict ou ChartOptions")
    chart = Chart(
        title=spec.get('title'),
        type=spec.get('type') or 'col',
        cat=_parse_fields(spec.get('cat'), '.cat'),
        value=_parse_fields(spec.get('value'), '.value'),
        stack=spec.get('stack') or {},
        label=_parse_label(spec.get('label')),
        options=options,
        limit=spec.get('limit'),
        legend=spec.get('legend') or options.legend,
    )
    return chart
