"""QSpec — espec declarativa de dados (query/pivot), camada pura do framework.

Genérico: não cita entidade do app. O app declara dicts (ex. QPLANO);
o motor resolve via parse_* (idempotente) e executa em core/qrun.

Ordem das props de query espelha o SQL:
  select, dist, from, join, where, groups, order, limit

select aceita por campo (estrutura espelha o Field):
  'nome'                                  -> coluna pura
  'alias': {agg, field}                   -> agregado GROUP BY (fora de over)
  'alias': {func, over={...}}             -> janela (func explícito, over nunca vazio)
  'alias': {over={agg, field, ...}}       -> agregado em janela
  'alias': {calc, pos_list, label, ...}   -> montado pós-over + apresentação
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
    # (label/width/align/format/pos_list) lado a lado, sem sub-dict display.
    name: str
    field: str = ''
    agg: Optional[str] = None
    func: Optional[str] = None
    over: Optional[OverSpec] = None
    calc: Optional[str] = None
    pos_list: int = 1
    label: Optional[str] = None
    width: Optional[float] = None
    align: Optional[str] = None
    format: Optional[str] = None

    def __post_init__(self):
        if self.agg and self.agg not in AGG_FUNCS:
            raise ValueError(f"select '{self.name}': agg desconhecida '{self.agg}'")
        if self.func and self.func not in OVER_FUNCS:
            raise ValueError(f"select '{self.name}': func desconhecida '{self.func}'")
        if self.pos_list not in (0, 1, 2):
            raise ValueError(f"select '{self.name}': pos_list deve ser 0|1|2")
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
                entries.append(SelectEntry(name=alias, field=alias))
            else:
                entries.append(_parse_entry(alias, cfg))
        return entries
    raise TypeError(f"select deve ser list ou dict, veio {type(select).__name__}")


ENTRY_KEYS = ('field', 'agg', 'func', 'over', 'calc', 'pos_list',
              'label', 'width', 'align', 'format')


def _parse_entry(alias, cfg) -> SelectEntry:
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
                       pos_list=int(cfg.get('pos_list', 1)),
                       label=cfg.get('label'), width=cfg.get('width'),
                       align=cfg.get('align'), format=cfg.get('format'))


def parse_aggs(aggs) -> list:
    """Dual curto/longo: {'id':'count'} | {'qtd':{'id':'count'}} -> [(alias,field,func)]."""
    out = []
    for alias, spec in (aggs or {}).items():
        if isinstance(spec, str):
            if spec not in AGG_FUNCS:
                raise ValueError(f"aggs '{alias}': função desconhecida '{spec}'")
            out.append((alias, alias, spec))
        elif isinstance(spec, dict):
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


@dataclass
class PivotSpec:
    src: Any = None
    lines: Any = None
    columns: Any = None
    aggs: Any = None
    filters: Any = None

    def __post_init__(self):
        self.rows = parse_pivot_aggs(self.aggs)


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
