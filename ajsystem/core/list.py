"""LIST — resolução de colunas, filtros e contexto de listagem.

Reescrito do zero observando `core/old/list.py`. Consome a resolução declarativa
de `defs.data` (merged `Entity(model)`+`Schema`). Helpers data-agnósticos para a
renderização de `pages/list.html` (cujos contratos são mantidos).
"""
import re

from ajsystem.defs.data import (
    Field, _resolve_fieldset, _entidade_fields, build_field,
)
from ajsystem.core.utils import currency_symbol
from ajsystem.defs.list import List, parse_list  # re-export (dataclass em `defs`)


def infer_filter_type(f: Field):
    inf = f.pos_filter
    if inf == 0 or inf == 9:
        return None
    if inf == 1:
        if f.input in ('date', 'datetime-local'):
            return 'date'
        if f.input == 'number':
            return 'number'
        if f.input == 'boolean':
            return 'boolean'
        return 'text'
    if inf == 2:
        return 'boolean' if f.input == 'boolean' else 'select'
    if inf == 3:
        return 'checklist'
    if f.input == 'boolean':
        return 'boolean'
    if f.input in ('date', 'datetime-local'):
        return 'date'
    if f.input == 'number':
        return 'number'
    if f.input == 'multi':
        return None
    if f.input == 'select' or f.options is not None:
        return 'select'
    return 'text'


def field_filter_options(f: Field):
    if f.options is not None:
        if isinstance(f.options, dict):
            return dict(f.options)  # preserva chaves: o filtro submete a chave
        return list(f.options)
    return None


def _cell_width_ch(text):
    """Largura visual aproximada de `text` em unidades `ch` (largura do '0').

    `ch` é a largura do glifo '0', tipicamente o mais estreito entre alfanuméricos
    em fontes não-tabulares. Para o conteúdo caber sem quebrar numa célula usamos
    pesos **conservadores**: dígitos/letras maiores que 1, para não subestimar.
    Cobre máscaras diversificadas (telefone, CPF/CNPJ, datas com nome de mês/dia
    da semana etc.).
    """
    w = 0.0
    for c in text:
        cu = c.upper()
        if cu.isalpha():
            w += 1.2 if cu in 'WM' else 1.05
        elif c.isdigit():
            w += 1.15
        elif c == ' ':
            w += 0.55
        elif c in '()[]':
            w += 0.6
        elif c in ',.:;':
            w += 0.55
        elif c in '-/\\':
            w += 0.65
        elif c == '@':
            w += 1.0
        else:
            w += 0.8
    return w


def _mask_width_ch(mask):
    """Largura estimada do maior conteúdo que a máscara pode formar.

    Substitui os curingas `9`/`A`/`a` pelos glifos mais largos possíveis e soma a
    largura dos literais. Máscaras com texto (datas longas, nome de mês, dia da
    semana) são cobertas genericamente aqui.
    """
    out = []
    for c in mask:
        if c == '9':
            out.append('8')
        elif c in 'Aa':
            out.append('W' if c == 'A' else 'w')
        elif c == 'X':
            out.append('W')
        else:
            out.append(c)
    return _cell_width_ch(''.join(out))


def _content_width_ch(f):
    """Largura em `ch` do conteúdo da célula, sem considerar o cabeçalho."""
    if f.mask and f.digits_only:
        return _mask_width_ch(f.mask)
    if f.options:
        labs = [str(v) for v in f.options.values()]
        return max((_cell_width_ch(ln) for ln in labs), default=0)
    if f.input in ('date', 'datetime-local', 'time'):
        fmt = {'date': 'dd/mm/aaaa',
               'datetime-local': 'dd/mm/aaaa hh:mm',
               'time': 'hh:mm'}[f.input]
        return _cell_width_ch(fmt)
    if f.input == 'number':
        dec = f.decimals if f.decimals is not None else 2
        body = '8' * 9
        if f.decimals is not None:
            body = '8' * 9 + ',' + '8' * max(dec, 0)
        s = body
        if f.currency:
            sym = currency_symbol(f.currency)
            s = (sym + ' ' if sym else '') + body
        if f.percent:
            s = body + ' %'
        return _cell_width_ch(s)
    if f.input in ('boolean', 'checkbox'):
        return _cell_width_ch('Falso')
    if f.input == 'select':
        return _cell_width_ch('Selecionar')
    return 0


def field_to_column(f: Field) -> dict:
    col = {'label': f.label or f.name, 'field': f.name, 'input': f.input}
    DEFAULT_WIDTHS = {'boolean': 6, 'number': 8, 'date': 12, 'select': 15}
    if f.width:
        w = f.width
    else:
        w = _content_width_ch(f) or DEFAULT_WIDTHS.get(f.input, 15)
    # cabeçalho: a palavra mais longa do label define um mínimo
    largest_word = max(len(x) for x in (f.label or f.name).split()) if (f.label or f.name) else 3
    if w < largest_word:
        w = largest_word
    col['width'] = int(w + 1)
    if f.align != 'left':
        col['align'] = f.align
    ft = infer_filter_type(f)
    if ft:
        col['filter'] = ft
    elif f.pos_filter == 0:
        col['filter'] = False
    fo = field_filter_options(f)
    if fo:
        col['filter_options'] = fo
    if f.mask:
        col['mask'] = f.mask
    if f.digits_only:
        col['digits_only'] = True
    if f.mask and f.digits_only:
        col['nowrap'] = True
    if f.decimals is not None:
        col['decimals'] = f.decimals
    if f.currency:
        col['currency'] = f.currency
    if f.percent:
        col['percent'] = True
    if f.options:
        col['options'] = f.options
    if f.calc:
        col['calc'] = f.calc
    if f.lookup:
        col['lookup'] = f.lookup
    if f.tag:
        col['tag'] = f.tag
    return col


def fields_to_columns(fields: list[Field]) -> list[dict]:
    return [field_to_column(f) for f in fields]


FILTER_MODES = {
    'text': [('igual', 'Igual a'), ('contains', 'Contém'), ('starts', 'Começa')],
    'number': [('igual', 'Igual a'), ('entre', 'Entre'),
               ('maior_que', 'Maior que'), ('maior_igual', 'Maior ou igual a'),
               ('menor_que', 'Menor que'), ('menor_igual', 'Menor ou igual a')],
    'date': [('hoje', 'Hoje'), ('ontem', 'Ontem'),
             ('ultimos_7_dias', 'Últimos 7 dias'),
             ('mes_atual', 'Mês Atual'), ('mes_anterior', 'Mês Anterior'),
             ('mes', 'Mês'), ('mes_ano', 'Mês/Ano'), ('ano_atual', 'Ano Atual'),
             ('ano_anterior', 'Ano Anterior'), ('ano', 'Ano'),
             ('ate_a_data_de', 'Até a data de'), ('a_partir_de', 'A partir de'),
             ('periodo', 'Período')],
    'boolean': [('', 'Todos'), ('true', 'Sim'), ('false', 'Não')],
    'select': [],
    'checklist': [],
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
        ftype = infer_filter_type(f)
        if not ftype:
            continue
        cfg = {'type': ftype, 'modes': FILTER_MODES.get(ftype, [])}
        cfg['label'] = f.display_label
        if ftype in ('select', 'checklist'):
            opts = field_filter_options(f)
            if opts:
                cfg['options'] = opts
        config[f.name] = cfg
    return config


def build_field_context(fields) -> dict:
    """Contexto de filtros/opções (estrutura mínima consumida pelo template)."""
    if isinstance(fields, dict):
        if 'fields' in fields:
            fields = _resolve_fieldset(fields)
        else:
            fields = [Field(name=k, **v) for k, v in _entidade_fields(fields).items()]
    ctx = {'filter_options': {}}
    for f in fields:
        ft = infer_filter_type(f)
        if ft == 'select':
            fo = field_filter_options(f)
            if fo is not None and f.name not in ctx['filter_options']:
                ctx['filter_options'][f.name] = fo
    return ctx


def _resolve_model(entity_name: str):
    from ajsystem.defs.data import MODEL_MAP
    key = re.sub(r'(?<!^)(?=[A-Z])', '_', entity_name).lower()
    if key in MODEL_MAP:
        return MODEL_MAP[key]
    import importlib
    module_path = f'app.models.{key}'
    try:
        mod = importlib.import_module(module_path)
    except ImportError:
        raise ImportError(f"Modelo não encontrado: {module_path}")
    model = getattr(mod, entity_name, None)
    if model is None:
        raise AttributeError(f"Classe {entity_name} não encontrada em {module_path}")
    return model


def resolve_column_configs(merged_entity: dict, spec, principal=None) -> list:
    """Resolve `spec` (str/de lista) para configs de campo a partir da entity
    merged `{campo: cfg}` (mesma semântica de `_resolve_cols` do legado).

    `str` bare = nome de uma entidade → expande todos os campos da entity
    merged (config = principal ou merged). `str`/item com `.` → campo específico.
    """
    config = principal or merged_entity
    if isinstance(spec, str):
        if spec in config:
            spec = [spec]
        else:
            # Mantém a ordem em que os campos foram definidos no dicionário (Python 3.7+ dict preserva ordem)
            spec = list((config or {}).keys())
    cols = []
    for item in spec or []:
        if isinstance(item, dict):
            name = (item.get('name') or '').split('.', 1)[-1]
            if not name:
                continue
            rest = {k: v for k, v in item.items() if k != 'name'}
            base = config.get(name, {}) or {}
            base = base if isinstance(base, dict) else {}
            cols.append(build_field(name, {**base, **rest}))
            continue
        field_name = item.split('.', 1)[-1]
        base = config.get(field_name, {}) or {}
        base = base if isinstance(base, dict) else {}
        cols.append(build_field(field_name, base))
    return cols
