"""LIST — resolução de colunas, filtros e contexto de listagem.

Reescrito do zero observando `core/old/list.py`. Consome a resolução declarativa
de `defs.data` (merged `Entity(model)`+`Schema`). Helpers data-agnósticos para a
renderização de `pages/list.html` (cujos contratos são mantidos).
"""
import re

from ajsystem import locales as i18n
from ajsystem.defs.data import (
    Field, _resolve_fieldset, _entidade_fields, build_field,
    normalize_fieldspec, _build_fields_from_names,
)
from ajsystem.core.utils import currency_symbol
from ajsystem.defs.list import List, parse_list  # re-export (dataclass em `defs`)


def infer_filter_type(f: Field):
    inf = f.pos_filter
    if inf == 0 or inf == 9:
        return None
    if inf == 1:
        # Filtro de texto renderiza o input como texto mesmo em data/número
        # (é o usuário que digita), então `select` cai em 'text'.
        kind = f.inp.filter_kind
        return 'text' if kind == 'select' else kind
    if inf == 2:
        return 'boolean' if f.inp.boolean else 'select'
    if inf == 3:
        return 'checklist'
    if f.inp.multi:
        return None
    # A ordem importa: `boolean`/`date`/`number` vencem `options` (um booleano
    # com `options` é checklist de filtro, não select), então o `filter_kind` do
    # catálogo é consultado antes do fallback por `options`.
    kind = f.inp.filter_kind
    return kind if kind != 'text' else ('select' if f.options is not None else 'text')


def field_filter_options(f: Field):
    if f.options is not None:
        if isinstance(f.options, dict):
            return dict(f.options)  # preserva chaves: o filtro submete a chave
        return list(f.options)
    # boolean sem options, mas checklist precisa Sim/Não
    if f.inp.boolean:
        return {'true': i18n.FILTER_YES, 'false': i18n.NO}
    _cached = getattr(f, '_fopts', _NO_OPTIONS)
    if _cached is not _NO_OPTIONS:
        return _cached
    opts = _lookup_filter_options(f)
    f._fopts = opts
    return opts


_NO_OPTIONS = object()


def _lookup_filter_options(f: Field):
    """Options de filtro para campo FK com lookup: consulta a tabela alvo.

    `f.lookup` é o dict resolvido por `resolve_lookup` (inclui `target`,
    `display`, `value` e opcional `when`). O `when` filtra a lista — o valor
    selecionado é a CHAVE (`value`, normalmente `id`); o filtro aplica sobre a
    coluna FK. `pos_filter: 1` força texto e `pos_filter: 0` retira do painel.
    """
    lk = getattr(f, 'lookup', None)
    if not isinstance(lk, dict):
        return None
    tgt = lk.get('target')
    if tgt is None or getattr(tgt, '__table__', None) is None:
        return None
    display = lk.get('display') or 'id'
    value = lk.get('value') or 'id'
    try:
        opts = getattr(tgt, 'query', None)
        if opts is None:
            return None
        when = lk.get('when')
        if when:
            from ajsystem.defs.data import apply_lookup_when
            opts = apply_lookup_when(opts, tgt, when)
        out = {}
        for row in opts.all():
            key = getattr(row, value, None)
            if key is None:
                continue
            label = getattr(row, display, None)
            if label is None:
                label = key
            out[str(key)] = str(label)
        return out
    except Exception:
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

    Substitui os curingas `9`/`A`/`N`/`#` pelos glifos mais largos possíveis e
    soma a largura dos literais. Máscaras com texto (datas longas, nome de mês,
    dia da semana) são cobertas genericamente aqui. Deve receber o corpo da
    máscara (`Field.mask_display`), sem o prefixo de comandos.
    """
    out = []
    for c in mask:
        if c == '9':
            out.append('8')
        elif c == 'A':
            out.append('W')
        elif c == 'N':
            out.append('W')
        elif c in 'a#':
            out.append('w')
        elif c == 'X':
            out.append('W')
        else:
            out.append(c)
    return _cell_width_ch(''.join(out))


def _content_width_ch(f):
    """Largura em `ch` do conteúdo da célula, sem considerar o cabeçalho."""
    if f.mask_display and f.input not in ('number', 'date', 'time', 'datetime-local'):
        return _mask_width_ch(f.mask_display)
    if f.options:
        labs = [str(v) for v in f.options.values()]
        return max((_cell_width_ch(ln) for ln in labs), default=0)
    if f.input in ('date', 'datetime-local', 'time'):
        fmt = {'date': 'dd/mm/aaaa',
               'datetime-local': 'dd/mm/aaaa hh:mm',
               'time': 'hh:mm'}[f.input]
        return _cell_width_ch(fmt)
    if f.inp.number:
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
    if f.inp.boolean:
        return _cell_width_ch('Falso')
    if f.inp.filter_kind == 'select':
        return _cell_width_ch('Selecionar')
    return 0


def field_to_column(f: Field) -> dict:
    col = {'label': f.label or f.name, 'field': f.name, 'input': f.input}
    if getattr(f, 'card_path', None):
        col['card_path'] = f.card_path
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
    if f.mask_cmds:
        col['mask_cmds'] = ''.join(sorted(f.mask_cmds))
    if f.mask_display and 'R' in f.mask_cmds:
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
    if getattr(f, 'stored', False):
        col['stored'] = True
    if f.lookup:
        col['lookup'] = f.lookup
    if f.tag:
        col['tag'] = f.tag
    return col


def fields_to_columns(fields: list[Field]) -> list[dict]:
    return [field_to_column(f) for f in fields]


def filter_modes() -> dict:
    """Modos de filtro por tipo inferido, na forma `[(modo, rótulo), ...]`.

    A primeira chave é o identificador de máquina (vai para o backend e não é
    traduzido); só o rótulo exibido sai do catálogo, que já vem resolvido na
    importação (ver `ajsystem/locales/__init__.py`). `text` e `number`
    compartilham `FILTER_EQ` de propósito — é o mesmo rótulo nos dois.
    """
    return {
        'text': [('igual', i18n.FILTER_EQ),
                 ('contains', i18n.FILTER_CONTAINS),
                 ('starts', i18n.FILTER_STARTS)],
        'number': [('igual', i18n.FILTER_EQ),
                   ('entre', i18n.FILTER_BETWEEN),
                   ('maior_que', i18n.FILTER_GT),
                   ('maior_igual', i18n.FILTER_GTE),
                   ('menor_que', i18n.FILTER_LT),
                   ('menor_igual', i18n.FILTER_LTE)],
        'date': [('hoje', i18n.FILTER_TODAY),
                 ('ontem', i18n.FILTER_YESTERDAY),
                 ('ultimos_7_dias', i18n.FILTER_LAST_7),
                 ('mes_atual', i18n.FILTER_THIS_MONTH),
                 ('mes_anterior', i18n.FILTER_LAST_MONTH),
                 ('mes', i18n.FILTER_MONTH),
                 ('mes_ano', i18n.FILTER_MONTH_YEAR),
                 ('ano_atual', i18n.FILTER_THIS_YEAR),
                 ('ano_anterior', i18n.FILTER_LAST_YEAR),
                 ('ano', i18n.FILTER_YEAR),
                 ('ate_a_data_de', i18n.FILTER_UNTIL),
                 ('a_partir_de', i18n.FILTER_FROM),
                 ('periodo', i18n.FILTER_PERIOD)],
        'boolean': [('', i18n.FILTER_ALL), ('true', i18n.FILTER_YES), ('false', i18n.NO)],
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
        cfg = {'type': ftype, 'modes': filter_modes().get(ftype, [])}
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


def resolve_column_configs(merged_entity: dict, spec, principal=None, pos_managed=None,
                           inputs=None) -> list:
    """Resolve `spec` para lista de Field usando normalização unificada.

    Mantém compatibilidade: recebe merged_entity single-entity e converte
    para full_schema esperado por normalize_fieldspec.
    """
    # Detecta se principal é multi-entity: chaves são nomes de entidade (PascalCase)
    # vs single-entity: chaves são nomes de campo (snake_case)
    is_multi_entity_principal = False
    if principal and isinstance(principal, dict):
        first_key = next(iter(principal.keys())) if principal else None
        if first_key and isinstance(principal.get(first_key), dict):
            # Heurística: se primeira chave parece nome de entidade (PascalCase)
            # E o valor tem chaves que parecem campos (snake_case)
            first_val = principal[first_key]
            if first_val and isinstance(first_val, dict):
                first_field_key = next(iter(first_val.keys())) if first_val else None
                # Verifica se first_key é PascalCase (entidade) E first_field_key é snake_case (campo)
                is_entity_key = first_key[0].isupper() if first_key else False
                is_field_key = first_field_key and ('_' in first_field_key or first_field_key.islower())
                if is_entity_key and is_field_key:
                    is_multi_entity_principal = True

    if is_multi_entity_principal:
        return normalize_fieldspec(spec, principal, principal, inputs=inputs)

    # Single-entity: merged_entity é {field: config}
    if isinstance(spec, str):
        if spec in merged_entity:
            # Campo específico
            spec = [spec]
            pos_m = False
        else:
            # Nome de entidade → expansão de todos os campos
            spec = list(merged_entity.keys())
            pos_m = True
        if pos_managed is not None:
            pos_m = bool(pos_managed)
        fields = _build_fields_from_names(spec, merged_entity, pos_m)
    else:
        # Lista ou dict (pode ser multi-entity no spec mas single no merged)
        # Tenta usar normalize_fieldspec com full_schema se spec for multi-entity dict
        if isinstance(spec, dict):
            first_val = next(iter(spec.values())) if spec else None
            if isinstance(first_val, list):
                # Spec é multi-entity dict {'Entity': ['f1']} mas merged é single
                # Para compat, trata como lista explícita no merged default
                # Achatamos todas as listas de campos
                all_fields = []
                for field_list in spec.values():
                    all_fields.extend(field_list)
                spec = all_fields
        
        # Usa normalize_fieldspec com entity 'default'
        full_schema = {'default': merged_entity}
        principal_dict = {'default': principal} if principal else {}
        fields = normalize_fieldspec(spec, full_schema, principal_dict, inputs=inputs)
        if pos_managed is not None:
            for f in fields:
                f._pos_managed = bool(pos_managed)

    return fields


# A construção de Fields a partir de nomes + merged fica em
# `defs/data._build_fields_from_names` (usada por `normalize_fieldspec` também).
# `_build_fields_from_merged` duplicava esse corpo e saiu.
