"""QSpec — espec declarativa de dados (query/pivot), camada pura do framework.

Genérico: não cita entidade do app. O app declara dicts (ex. QPLANO);
o motor resolve via parse_* (idempotente) e executa em core/qrun.

Ordem das props de query espelha o SQL:
  select, dist, from, join, where, groups, order, limit

`where` usa a gramática literal dos filtros (dict/lista = AND,
OR(...)/AND(...), sentinelas, operadores e IN); o executor compila com cast
pelo tipo do field e aplica antes dos OVERs.

select aceita por campo (estrutura espelha o Field):
  'nome'                                  -> coluna pura
  'alias': {agg, field}                   -> agregado GROUP BY (fora de over)
  'alias': {func, over={...}}             -> janela (func explícito, over nunca vazio)
  'alias': {over={agg, field, ...}}       -> agregado em janela
  'alias': {calc, label, width, ...}      -> montado pós-over + apresentação

Ordem do select = ordem de exibição. Avaliação independe dela: overs (e
aggs) antes dos calcs; calc referencia coluna ou over/agg, nunca outro calc.

A entrada NÃO posiciona campo: se algo é coluna, card ou oculto é a página,
nos slots `line`/`card`/`hidden` de `Page.props.list` (`core.resolve.
resolve_slots`). Um `select` compartilhado entre listagem e report é lido
pelos dois sem que nenhum dos dois precise saber do display do outro.
"""
from dataclasses import dataclass, field as dc_field
from typing import Any, Optional

QUERY_KEYS = ('select', 'dist', 'from', 'join', 'where', 'groups',
              'order', 'limit', 'levels')
PIVOT_KEYS = ('src', 'lines', 'columns', 'aggs', 'filters')

OVER_FUNCS = ('rownumber', 'rank', 'denserank', 'percentrank', 'cumedist',
              'ntile', 'lag', 'lead', 'firstvalue', 'lastvalue',
              'nthvalue', 'sum', 'avg', 'min', 'max', 'count')
AGG_FUNCS = ('count', 'sum', 'avg', 'min', 'max')

# Registro de expressões liberadas em order (extensível, uma por vez, com
# aprovação). Hoje: só coalesce. Formato: {coalesce: [campo, ...]}.
EXPR_FUNCS = {
    'coalesce': {'min': 2, 'args': 'fields'},
}


def parse_order_item(item):
    """Normaliza 1 item de order -> ('field', nome, desc) | ('expr', func, fields, desc).

    Aceita: 'nome', 'nome desc', {field, direction}, {coalesce: [...]}.
    """
    if isinstance(item, str):
        parts = item.split()
        return ('field', parts[0], len(parts) > 1 and parts[1].lower() == 'desc')
    if isinstance(item, dict):
        item = dict(item)
        direction = str(item.pop('direction', 'asc')).lower() == 'desc'
        if 'field' in item and len(item) == 1:
            return ('field', item['field'], direction)
        if len(item) == 1:
            (fn, args), = item.items()
            if fn not in EXPR_FUNCS:
                raise ValueError(f"order: expressão '{fn}' não liberada {sorted(EXPR_FUNCS)}")
            if not isinstance(args, (list, tuple)) or len(args) < EXPR_FUNCS[fn]['min']:
                raise ValueError(f"order: '{fn}' exige ao menos {EXPR_FUNCS[fn]['min']} campos")
            return ('expr', fn, list(args), direction)
        raise ValueError(f"order: item dict inválido {item}")
    raise TypeError(f"order: item deve ser str ou dict, veio {type(item).__name__}")


def normalize_order(order):
    if not order:
        return []
    if isinstance(order, (str, bytes)):
        order = [order]
    return [parse_order_item(i) for i in order]


def is_query_dict(spec) -> bool:
    """dict com cara de query: tem select+from (detecção p/ columns polimórfica)."""
    return isinstance(spec, dict) and 'select' in spec and 'from' in spec


def is_pivot_dict(spec) -> bool:
    """dict (ou PivotSpec) com cara de pivot: tem src+lines."""
    if isinstance(spec, PivotSpec):
        return True
    return isinstance(spec, dict) and 'src' in spec and 'lines' in spec


def _norm_list(v):
    if v is None:
        return []
    if isinstance(v, (str, bytes)):
        return [v]
    return list(v)


@dataclass
class OverSpec:
    func: Optional[str] = None
    agg: Optional[str] = None
    field: str = ''
    partition: list = dc_field(default_factory=list)
    order: list = dc_field(default_factory=list)
    frame: Optional[dict] = None
    offset: int = 1
    default: Any = None
    count: int = 4

    def __post_init__(self):
        if not self.func and not self.agg:
            raise ValueError("over exige 'func' ou 'agg' (over nunca vazio)")
        if self.func and self.func not in OVER_FUNCS:
            raise ValueError(f"over.func desconhecida '{self.func}': {sorted(OVER_FUNCS)}")
        if self.agg and self.agg not in AGG_FUNCS:
            raise ValueError(f"over.agg desconhecida '{self.agg}': {sorted(AGG_FUNCS)}")
        self.partition = _norm_list(self.partition)
        self.order = _norm_list(self.order)
        self.okeys = normalize_order(self.order)
        if self.func in ('ntile', 'nthvalue') and (not self.count or self.count < 1):
            raise ValueError(f"over.func '{self.func}' exige 'count' >= 1")


@dataclass
class SelectEntry:
    # Estrutura espelha o Field: dado (field/agg/func/over/calc) + apresentação
    # (label/width/align/format) lado a lado, sem sub-dict display. A posição
    # (coluna/card/oculto) não mora aqui — é da página que consome (`line`,
    # `card`, `hidden`).
    name: str
    field: str = ''
    agg: Optional[str] = None
    func: Optional[str] = None
    over: Optional[OverSpec] = None
    calc: Optional[str] = None
    label: Optional[str] = None
    width: Optional[float] = None
    align: Optional[str] = None
    format: Optional[str] = None

    def __post_init__(self):
        if self.agg and self.agg not in AGG_FUNCS:
            raise ValueError(f"select '{self.name}': agg desconhecida '{self.agg}'")
        if self.func and self.func not in OVER_FUNCS:
            raise ValueError(f"select '{self.name}': func desconhecida '{self.func}'")
        if self.align is not None and self.align not in ('left', 'center', 'right'):
            raise ValueError(f"select '{self.name}': align deve ser left|center|right")


def parse_select(select) -> list:
    """Normaliza select (list/set/dict) p/ [SelectEntry]. Dual curto/longo p/ aggs."""
    entries = []
    if select is None:
        return entries
    if isinstance(select, (list, tuple, set)):
        for item in select:
            if isinstance(item, str):
                entries.append(SelectEntry(name=item, field=item))
            elif isinstance(item, dict):
                for alias, cfg in item.items():
                    entries.append(_parse_entry(alias, cfg))
            else:
                raise TypeError(f"select: item deve ser str ou dict, veio {type(item).__name__}")
        return entries
    if isinstance(select, dict):
        for alias, cfg in select.items():
            if cfg is None or isinstance(cfg, str) and not cfg:
                entries.append(SelectEntry(name=alias, field=alias))
            elif isinstance(cfg, str):
                entries.append(SelectEntry(name=alias, field=cfg))
            else:
                entries.append(_parse_entry(alias, cfg))
        return entries
    raise TypeError(f"select deve ser list ou dict, veio {type(select).__name__}")


ENTRY_KEYS = ('field', 'agg', 'func', 'over', 'calc',
              'label', 'width', 'align', 'format')


def _parse_entry(alias, cfg) -> SelectEntry:
    if isinstance(cfg, str):
        return SelectEntry(name=alias, field=cfg)
    if not isinstance(cfg, dict):
        raise TypeError(f"select '{alias}': cfg deve ser dict, veio {type(cfg).__name__}")
    cfg = dict(cfg)
    unknown = [k for k in cfg if k not in ENTRY_KEYS]
    if unknown:
        raise ValueError(f"select '{alias}': chaves desconhecidas {unknown} (aceitas {list(ENTRY_KEYS)})")
    over = cfg.pop('over', None)
    agg = cfg.pop('agg', None)
    func = cfg.pop('func', None)
    fld = cfg.pop('field', alias)
    over_spec = None
    if over is not None:
        if not isinstance(over, dict):
            raise TypeError(f"select '{alias}': over deve ser dict")
        over = dict(over)
        # agg dentro de over (forma travada) -> promove p/ OverSpec.agg
        oagg = over.pop('agg', None)
        ofunc = over.pop('func', func)
        over_spec = OverSpec(func=ofunc, agg=oagg or None,
                             field=over.pop('field', fld),
                             partition=over.pop('partition', []),
                             order=over.pop('order', []),
                             frame=over.pop('frame', None),
                             offset=over.pop('offset', 1),
                             default=over.pop('default', None),
                             count=over.pop('count', 4))
        if over:
            raise ValueError(f"select '{alias}': over com chaves desconhecidas {sorted(over)}")
        # agg/form fora + over com agg = duplicado
        if agg and over_spec.agg:
            raise ValueError(f"select '{alias}': agg dentro e fora de over (escolha um)")
        agg = agg or None
        func = None
    return SelectEntry(name=alias, field=fld, agg=agg, func=func,
                       over=over_spec, calc=cfg.get('calc'),
                       label=cfg.get('label'), width=cfg.get('width'),
                       align=cfg.get('align'), format=cfg.get('format'))


def parse_aggs(aggs) -> list:
    """Dual curto/longo: {'id':'count'} | {'qtd':{'id':'count'}} -> [(alias,field,func)].

    Também aceita a forma explícita ``{'total': {'field': 'valor', 'agg': 'sum'}}``
    (a mesma leitura do resto do QSpec, sem depender de um único par chave:fn).
    """
    out = []
    for alias, spec in (aggs or {}).items():
        if isinstance(spec, str):
            if spec not in AGG_FUNCS:
                raise ValueError(f"aggs '{alias}': função desconhecida '{spec}'")
            out.append((alias, alias, spec))
        elif isinstance(spec, dict):
            if 'agg' in spec or 'field' in spec:
                fld = spec.get('field', alias)
                fn = spec.get('agg')
                if fn not in AGG_FUNCS:
                    raise ValueError(f"aggs '{alias}': função desconhecida '{fn}'")
                out.append((alias, fld, fn))
                continue
            if len(spec) != 1:
                raise ValueError(f"aggs '{alias}': forma longa exige 1 par {{field: func}}")
            (fld, fn), = spec.items()
            if fn not in AGG_FUNCS:
                raise ValueError(f"aggs '{alias}': função desconhecida '{fn}'")
            out.append((alias, fld, fn))
        else:
            raise TypeError(f"aggs '{alias}': deve ser str ou dict")
    return out


@dataclass
class QuerySpec:
    select: Any = None
    dist: bool = False
    desc: Any = None  # 'from' via getattr (palavra reservada)
    join: Any = None
    where: Any = None
    groups: Any = None
    order: Any = None
    limit: int = 0
    levels: Any = None

    def __post_init__(self):
        self.entries = parse_select(self.select)
        if self.groups and not any(e.agg for e in self.entries):
            raise ValueError("query com 'groups' exige ao menos um campo com 'agg'")


def parse_query(spec) -> QuerySpec:
    """dict|QuerySpec -> QuerySpec (idempotente). Só aceita chaves SQL."""
    if isinstance(spec, QuerySpec):
        return spec
    if not isinstance(spec, dict):
        raise TypeError(f"query deve ser dict, veio {type(spec).__name__}")
    spec = dict(spec)
    if 'hierarchy' in spec:
        if 'levels' not in spec:
            spec['levels'] = spec.pop('hierarchy')  # alias legado
        else:
            spec.pop('hierarchy')  # levels vence
    unknown = [k for k in spec if k not in QUERY_KEYS]
    if unknown:
        raise ValueError(f"query: chaves desconhecidas {unknown} (aceitas {list(QUERY_KEYS)})")
    return QuerySpec(select=spec.get('select'), dist=bool(spec.get('dist', False)),
                     desc=spec.get('from'), join=spec.get('join'),
                     where=spec.get('where', {}), groups=spec.get('groups'),
                     order=spec.get('order'), limit=int(spec.get('limit') or 0),
                     levels=spec.get('levels'))


AXIS_KEYS = ('field', 'name', 'label', 'width', 'align', 'format', 'values')


@dataclass
class AxisSpec:
    """Eixo do pivot (linha ou coluna) — dado + apresentação, como o Field.

    `name` é o atributo que a linha resultante assume (o alias); `field` é o
    caminho no `src`. `values` só vale no eixo de coluna: fixa o conjunto/ordem
    das colunas geradas (sem ele, os valores são descobertos nos dados).
    """
    name: str
    field: str = ''
    label: Optional[str] = None
    width: Optional[float] = None
    align: Optional[str] = None
    format: Optional[str] = None
    values: Optional[list] = None

    def __post_init__(self):
        if not self.name:
            raise ValueError("pivot: eixo sem 'name'")
        if not self.field:
            self.field = self.name
        if self.align is not None and self.align not in ('left', 'center', 'right'):
            raise ValueError(f"pivot '{self.name}': align deve ser left|center|right")


def parse_axis(item, where='pivot', allow_values=False) -> AxisSpec:
    """Normaliza 1 eixo -> AxisSpec.

    Aceita `'campo'`, `{'field': 'campo', ...}` e a forma do select
    `{'alias': 'campo'}` / `{'alias': {props}}`.
    """
    if isinstance(item, AxisSpec):
        return item
    if isinstance(item, str):
        return AxisSpec(name=item, field=item)
    if not isinstance(item, dict):
        raise TypeError(f"{where}: eixo deve ser str ou dict, veio {type(item).__name__}")
    cfg = dict(item)
    if 'field' in cfg:
        fld = cfg.pop('field')
        if not isinstance(fld, str) or not fld:
            raise ValueError(f"{where}: 'field' deve ser str")
        name = cfg.pop('name', None) or fld
    elif len(cfg) == 1:
        (name, spec), = cfg.items()
        if isinstance(spec, str):
            fld, cfg = spec, {}
        elif isinstance(spec, dict):
            cfg = dict(spec)
            fld = cfg.pop('field', name)
        else:
            raise TypeError(f"{where} '{name}': cfg deve ser str ou dict")
    else:
        raise ValueError(f"{where}: eixo dict inválido {item}")
    unknown = [k for k in cfg if k not in AXIS_KEYS]
    if unknown:
        raise ValueError(f"{where} '{name}': chaves desconhecidas {unknown} (aceitas {list(AXIS_KEYS)})")
    values = cfg.pop('values', None)
    if values is not None:
        if not allow_values:
            raise ValueError(f"{where} '{name}': 'values' só vale no eixo de coluna")
        values = _norm_list(values)
        if len(set(values)) != len(values):
            raise ValueError(f"{where} '{name}': 'values' tem valor repetido")
    # path pontilhado sem alias explícito vira atributo seguro
    if name == fld and '.' in name:
        name = name.replace('.', '_')
    return AxisSpec(name=name, field=fld, values=values, **cfg)


@dataclass
class PivotSpec:
    src: Any = None
    lines: Any = None
    columns: Any = None
    aggs: Any = None
    filters: Any = None

    def __post_init__(self):
        if not self.src:
            raise ValueError("pivot: 'src' é obrigatório (QuerySpec ou entidade)")
        self.line_axes = [parse_axis(x, 'pivot.lines') for x in _norm_list(self.lines)]
        if not self.line_axes:
            raise ValueError("pivot: 'lines' exige ao menos um eixo")
        cols = self.columns
        if isinstance(cols, (list, tuple)):
            if len(cols) != 1:
                raise ValueError("pivot: 'columns' aceita um eixo (multi-nível é fase 2)")
            cols = cols[0]
        if cols is None:
            raise ValueError("pivot: 'columns' é obrigatório")
        self.column_axis = parse_axis(cols, 'pivot.columns', allow_values=True)
        self.measures = parse_pivot_aggs(self.aggs)
        if not self.measures:
            raise ValueError("pivot: 'aggs' exige ao menos uma medida")
        self.rows = self.measures  # compat: nome anterior dos agregados


def parse_pivot_aggs(aggs):
    return parse_aggs(aggs)


def parse_pivot(spec) -> PivotSpec:
    if isinstance(spec, PivotSpec):
        return spec
    if not isinstance(spec, dict):
        raise TypeError(f"pivot deve ser dict, veio {type(spec).__name__}")
    unknown = [k for k in spec if k not in PIVOT_KEYS]
    if unknown:
        raise ValueError(f"pivot: chaves desconhecidas {unknown} (aceitas {list(PIVOT_KEYS)})")
    return PivotSpec(src=spec.get('src'), lines=_norm_list(spec.get('lines')),
                     columns=spec.get('columns'), aggs=spec.get('aggs'),
                     filters=spec.get('filters', {}))
