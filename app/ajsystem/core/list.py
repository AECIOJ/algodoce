"""
XXX_LIST / XXX_FIELDS — Configuração de listas e campos de listagem.

Cada rota sys_*.py declara:
  XXX_FIELDS = [Field(...), ...]          # lista de campos
  XXX_LIST   = List(fields=XXX_FIELDS, ...)  # config da lista

O dataclass `Field` e a construção/resolução de campos vivem em
`app.ajsystem.defs.entities` (camada de dados); este módulo trata apenas da
renderização de listas (`List`, colunas, filtros).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Field — configuração de uma coluna
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 Campo            Tipo       Default   Descrição
 ──────────────── ────────── ───────── ──────────────────────────────────
 name             str        (obrig.)  Nome do campo (chave do dict)
 label            str        name      Título da coluna
 width            int        auto      Largura em caracteres (ch)
 align            str        'left'    'left' | 'right' | 'center'
 input            str        'text'    Tipo do campo (define filtro auto):
                                        'text'    → filtro texto
                                        'number'  → filtro numérico
                                        'date'    → filtro data
                                        'boolean' → filtro Sim/Não
                                        'select'  → filtro select
 options          dict       None      Opções para select: {chave: label}
 filter           str|False  auto      Tipo do filtro forçado, ou False p/ desabilitar
 filter_options   list       None      Opções customizadas para o filtro select
 mask             str        None      Máscara de formatação (ex: '999.999')
 query            str        None      Chave do MODEL_MAP p/ popular options do banco
 validate         list       None      Regras de validação no form
 aggregate        str        None      'sum' p/ exibir total no rodapé
 aggregate_label  str        None      Label do total (ex: 'Total Geral')
 currency         str        None      'brl' p/ formatar como moeda R$
 hide_zero        bool       True      Ocultar valor zero
 card_path        str        None      Acesso aninhado (ex: 'conta.nome')
 link             str        None      Endpoint p/ gerar link (ex: 'orders.edit')
 function         callable   None      Função para valor computado: f(item) -> valor
 rows             int        1         Altura do textarea no form (nº de linhas)
 in_form          bool       True      `False` exclui o campo do form (nem exibe nem submete)
 in_list          int(0|1|2) 1        `0` exclui da listagem/card/filtro; `1` coluna na linha (vai p/ o card quando não couber); `2` sempre no card. `True`→1, `False`→0
 transform        str|callable  auto   Transformação ao salvar: 'title' (padrão em textos editáveis), 'cap', 'upper', 'lower', 'none' ou callable(val, field)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 List — configuração da lista
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 Campo              Tipo       Default   Descrição
 ────────────────── ────────── ───────── ──────────────────────────────────
 fields             list       (obrig.)  Lista de Field
 fields_master      list[int]  None      Índices 1-based dos campos mestre (master-detail)
 fields_detail      list[int]  None      Índices 1-based dos campos detalhe (master-detail)
 master_key         str        None      Campo para groupby no master-detail
 edit_endpoint      str        None      Endpoint de edição (ex: 'orders.edit')
 edit_id_field      str        'id'      Campo que contém o ID para edição
 edit_if_field      str        None      Só exibe edição se este campo for não-nulo
 edit_endpoint_map  dict       None      Mapa de endpoints por tipo
 edit_endpoint_key  str        None      Chave do item para lookup no edit_endpoint_map
 detail_data        str        None      Atributo com sub-itens do detalhe
 reports            list       None      Lista de Report vinculados

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Exemplos
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 Simples:
   Field(name='nome', label='Nome', width=20, pos=1)

 Select do banco:
   Field(name='categoria', label='Categoria', width=15, query='category')

 Master-detail:
   List(fields=FIELDS, fields_master=[1,2,3], fields_detail=[4,5,6],
        master_key='pai_id', edit_endpoint='filhos.edit')
"""
import importlib
import re

from sqlalchemy import text

from typing import Optional

from app.ajsystem.defs.fields import Field
from app.ajsystem.defs.query import _resolve_query
from app.ajsystem.defs.entities import (
    _resolve_fieldset, _entidade_fields, MODEL_MAP, build_field_config,
)
from app.ajsystem.defs.list import List  # noqa: F401


def field_filter_type(f: Field) -> Optional[str]:
    if f.filter is not None:
        if isinstance(f.filter, dict):
            return f.filter.get('type')
        if isinstance(f.filter, str):
            return f.filter
        if f.filter is False:
            return None
    if f.input == 'boolean':
        return 'boolean'
    if f.input == 'date':
        return 'date'
    if f.input == 'number':
        return 'number'
    if f.input == 'select':
        return 'select'
    if f.options is not None:
        return 'select'
    if f.filter_options is not None:
        return 'select'
    if f.query is not None:
        return 'select'
    return 'text'


def field_filter_options(f: Field):
    if f.filter_options is not None:
        return f.filter_options
    if f.options is not None:
        if isinstance(f.options, dict):
            return list(f.options.values())
        return list(f.options)
    q = _resolve_query(f.query)
    if q is not None:
        try:
            model = MODEL_MAP.get(q.model)
            if model and hasattr(model, 'query'):
                query = model.query
                if q.when:
                    query = query.filter(text(q.when))
                items = query.order_by(q.order or q.field).all()
                return [str(getattr(o, q.field, o)) for o in items if getattr(o, q.field, None)]
        except Exception:
            pass
    return None


def field_to_column(f: Field) -> dict:
    col = {'label': f.label or f.name, 'field': f.name, 'input': f.input}
    DEFAULT_WIDTHS = {'boolean': 6, 'number': 8, 'date': 12, 'select': 15}
    w = f.width or DEFAULT_WIDTHS.get(f.input, 15)
    largest_word = max(len(w) for w in (f.label or f.name).split())
    if w < largest_word:
        w = largest_word
    col['width'] = w + 1
    if f.align != 'left':
        col['align'] = f.align
    ft = field_filter_type(f)
    if ft:
        col['filter'] = ft
    elif f.filter is False:
        col['filter'] = False
    fo = field_filter_options(f)
    if fo:
        col['filter_options'] = fo
    if f.mask:
        col['mask'] = f.mask
    if f.digits_only:
        col['digits_only'] = True
    if f.decimals is not None:
        col['decimals'] = f.decimals
    if f.currency:
        col['currency'] = f.currency
    if f.hide_zero:
        col['hide_zero'] = True
    if f.card_path:
        col['card_path'] = f.card_path
    if f.options:
        col['options'] = f.options
    if f.link:
        col['link'] = f.link
    if f.function:
        col['function'] = f.function
    if f.aggregate:
        col['aggregate'] = f.aggregate
        if f.aggregate_label:
            col['aggregate_label'] = f.aggregate_label
    return col


def fields_to_columns(fields: list[Field]) -> list[dict]:
    return [field_to_column(f) for f in fields]


FILTER_MODES = {
    'text': [('igual', 'Igual a'), ('contains', 'Contém'), ('starts', 'Começa')],
    'number': [('igual', 'Igual a'), ('entre', 'Entre'),
               ('maior_que', 'Maior que'), ('maior_igual', 'Maior ou igual a'),
               ('menor_que', 'Menor que'), ('menor_igual', 'Menor ou igual a')],
    'date': [('hoje', 'Hoje'), ('periodo', 'Período'), ('ontem', 'Ontem'),
             ('ultimos_7_dias', 'Últimos 7 dias'), ('mes', 'Mês'),
             ('mes_atual', 'Mês Atual'), ('mes_anterior', 'Mês Anterior'),
             ('ano', 'Ano'), ('ano_atual', 'Ano Atual'),
             ('a_partir_de', 'A partir de'), ('ate_a_data_de', 'Até a data de')],
    'boolean': [('', 'Todos'), ('true', 'Sim'), ('false', 'Não')],
    'select': [],
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
        if f.filter is False:
            continue

        if isinstance(f.filter, dict):
            cfg = {**f.filter}
            if cfg.get('type') == 'select' and 'options' not in cfg:
                opts = field_filter_options(f)
                if opts:
                    cfg['options'] = opts
            if f.filter_path:
                cfg['filter_path'] = f.filter_path
            cfg.setdefault('label', f.display_label)
            config[f.name] = cfg
            continue

        ftype = f.filter if isinstance(f.filter, str) else field_filter_type(f)
        if not ftype:
            continue

        cfg = {'type': ftype, 'modes': FILTER_MODES.get(ftype, [])}
        cfg['label'] = f.display_label
        if ftype == 'select':
            opts = field_filter_options(f)
            if opts:
                cfg['options'] = opts if isinstance(opts, list) else list(opts.values()) if isinstance(opts, dict) else opts
        if f.filter_path:
            cfg['filter_path'] = f.filter_path
        config[f.name] = cfg

    return config


def build_field_context(fields: list[Field] | dict) -> dict:
    from flask import current_app

    if isinstance(fields, dict):
        if 'fields' in fields:
            fields = _resolve_fieldset(fields)
        else:
            fields = [Field(name=k, **v) for k, v in _entidade_fields(fields).items()]
    ctx = {'filter_options': {}}
    with current_app.app_context():
        for f in fields:
            q = _resolve_query(f.query)
            if q is not None:
                model = MODEL_MAP.get(q.model)
                if model and hasattr(model, 'query'):
                    query = model.query
                    if q.when:
                        query = query.filter(text(q.when))
                    items = query.order_by(q.order or q.field).all()
                    names = [str(getattr(o, q.field, o)) for o in items if getattr(o, q.field, None)]
                    if f.filter_options is None:
                        f.filter_options = names
                    if f.options is None:
                        f.options = {str(getattr(o, 'id', o)): str(getattr(o, q.field, o)) for o in items if getattr(o, q.field, None)}
            ft = field_filter_type(f)
            if ft == 'select':
                fo = field_filter_options(f)
                if fo is not None and f.name not in ctx['filter_options']:
                    ctx['filter_options'][f.name] = fo
    return ctx


def field_grid(f: Field) -> int:
    if f.grid:
        return f.grid
    if f.input == 'textarea':
        return 12
    if f.input in ('boolean', 'checkbox'):
        return 2
    w = f.width or 12
    if w <= 4:
        return 2
    if w <= 8:
        return 3
    if w <= 14:
        return 4
    if w <= 24:
        return 6
    return 8




def _resolve_model(entity_name: str):
    key = re.sub(r'(?<!^)(?=[A-Z])', '_', entity_name).lower()
    if key in MODEL_MAP:
        return MODEL_MAP[key]
    module_path = f'app.models.{key}'
    try:
        mod = importlib.import_module(module_path)
    except ImportError:
        raise ImportError(f"Modelo não encontrado: {module_path}")
    model = getattr(mod, entity_name, None)
    if model is None:
        raise AttributeError(f"Classe {entity_name} não encontrada em {module_path}")
    return model


def _resolve_cols(fields, entidades, principal=None) -> list:
    """Resolve `List.fields` para configs de campo, espelhando o `Form.fields`:
    - str 'Entidade' → expande todos os campos da entity;
    - 'Entidade.campo' → campo específico;
    - nome simples → campo da entity principal;
    - dict {'name': ..., **cfg} → campo com override.
    """
    if isinstance(fields, str):
        items = [fields]
    else:
        items = fields
    cols = []
    for item in items:
        if isinstance(item, dict):
            name = item.get('name')
            if not name:
                continue
            rest = {k: v for k, v in item.items() if k != 'name'}
            if '.' in name:
                entity, field_name = name.split('.', 1)
                config = entidades.get(entity, {})
            else:
                field_name = name
                config = principal or {}
            base = config.get(field_name, {}) if isinstance(config, dict) else {}
            base = base if isinstance(base, dict) else {}
            cols.append(build_field_config(field_name, {**base, **rest}))
            continue
        if '.' in item:
            entity, field_name = item.split('.', 1)
        else:
            entity = item
            field_name = None
        if field_name:
            if entity in entidades:
                config = entidades[entity]
                cols.append(build_field_config(field_name, config[field_name]))
            elif principal:
                config = principal
                cols.append(build_field_config(entity, config[entity]))
        else:
            config = entidades[entity] if entity in entidades else principal
            for name, cfg in _entidade_fields(config).items():
                cols.append(build_field_config(name, cfg))
    return cols


def _resolve_field_names(items: list) -> list[str]:
    names = []
    for item in items:
        if '.' in item:
            _, field_name = item.split('.', 1)
            names.append(field_name)
        else:
            names.append(item)
    return names
