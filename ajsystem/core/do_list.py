"""Orquestrador `do_list` — request → response para listagens.

Reescrito do zero observando `core/old/do_list.py`. Lê `Page`/`Schema` (dicts
declarativos) do módulo de rota e resolve os campos via `defs.data`
(merge `Entity(model)` + `Schema`). Mantém os contratos de render de
`pages/list.html`.
"""
import importlib

from flask import current_app, render_template, request, url_for

from ajsystem import locales as i18n
from ajsystem.defs.data import (
    _auto_label, build_field, page_filter_cfg, page_list_cfg, page_report_cfg,
    page_scripts, resolve_entity_fields, module_page, resolve_max_width,
)
from ajsystem.core.list import (
    List, build_field_context, resolve_column_configs,
    fields_to_columns, _resolve_model,
)
from ajsystem.core.resolve import resolve_slots
from ajsystem.core.filters import resolve_filter
from ajsystem.core.utils import module_blueprint, normalizar_slug

TAB_TYPES = ('List', 'Filter', 'Report', 'Custom')

# Aba Relatórios (§5.6.2): operador declarado por campo em `props.report`.
# O símbolo é o comparador; em `date`, `>`/`<` são inclusivos (a partir de/até).
REPORT_OPS = ('=', '!=', '>', '>=', '<', '<=', 'like', '<>')

_REPORT_OPS_BY_TYPE = {
    'text': ('=', '!=', 'like'),
    'number': ('=', '!=', '>', '>=', '<', '<=', '<>'),
    'date': ('=', '!=', '>', '>=', '<', '<=', '<>'),
    'boolean': ('=', '!='),
    'select': ('=', '!='),
    'checklist': ('=', '!='),
}

_REPORT_OP_LABEL = {
    'text': {'=': i18n.FILTER_EQ, '!=': i18n.FILTER_NEQ,
             'like': i18n.FILTER_CONTAINS},
    'number': {'=': i18n.FILTER_EQ, '!=': i18n.FILTER_NEQ,
               '>': i18n.FILTER_GT, '>=': i18n.FILTER_GTE,
               '<': i18n.FILTER_LT, '<=': i18n.FILTER_LTE,
               '<>': i18n.FILTER_BETWEEN},
    'date': {'=': i18n.FILTER_ON_DATE, '!=': i18n.FILTER_NEQ,
             '>': i18n.FILTER_FROM, '>=': i18n.FILTER_FROM,
             '<': i18n.FILTER_UNTIL, '<=': i18n.FILTER_UNTIL,
             '<>': i18n.FILTER_PERIOD},
    'boolean': {'=': i18n.FILTER_EQ, '!=': i18n.FILTER_NEQ},
    'select': {'=': i18n.FILTER_EQ, '!=': i18n.FILTER_NEQ},
    'checklist': {'=': i18n.FILTER_CONTAINS, '!=': i18n.FILTER_NEQ},
}


def _default_type(key):
    norm = (key or '').strip().lower()
    if norm == 'dados':
        return 'List'
    if norm in ('filtros', 'filtrar'):
        return 'Filter'
    if norm == 'relatorios' or norm == 'relatório' or norm == 'relatórios' or norm == 'reports' or norm == 'report':
        return 'Report'
    return 'Custom'


def _total_ch(fields, edit_endpoint) -> str:
    """`ch` da soma das colunas + ações — cálculo compartilhado pela listagem."""
    tot = sum(col['width'] for col in fields_to_columns(fields))
    tot += 16 if edit_endpoint else 0
    tot += 3
    return f'{tot}ch'


def _list_default_max_width(lista: List) -> str:
    """Largura padrão de lista sem `max_width`: soma das colunas + ações.

    Espelha o cálculo que antes vivia em `pages/list.html` (`tot_ch`).
    """
    return _total_ch(lista.master_fields, lista.edit_endpoint)


_CSS_WIDTH_KEYWORDS = {'auto', 'none', 'initial', 'inherit', 'unset',
                       'revert', 'revert-layer'}


def _ch_value(width):
    """`'67ch'` → `67` (para `tab.max_width`); outra unidade CSS → `None`."""
    txt = str(width or '').strip()
    if not txt.endswith('ch'):
        return None
    try:
        num = float(txt[:-2])
    except ValueError:
        return None
    if num <= 0:
        return None
    return int(num) if num.is_integer() else num


def _list_page_width(lista: List, list_obj: List, tabs, filter_width) -> str:
    """Largura do container da listagem: a maior entre lista e painel.

    A aba Dados continua presa à largura da lista (`tab.max_width`), então o
    painel chega ao seu cap (`filter.max_width`) sem alargar a tabela. Quando o
    cap do painel não é um comprimento CSS utilizável, o container fica na
    largura da lista.
    """
    list_width = (resolve_max_width(lista.get('max_width'))
                  or _list_default_max_width(list_obj))
    for tab in tabs:
        if tab.get('type') == 'List':
            tab['max_width'] = _ch_value(list_width)
    filter_width = str(filter_width or '').strip()
    if not filter_width or filter_width.lower() in _CSS_WIDTH_KEYWORDS:
        return list_width
    list_ch, filter_ch = _ch_value(list_width), _ch_value(filter_width)
    if list_ch is not None and filter_ch is not None:
        return f'{max(list_ch, filter_ch):g}ch'
    return f'max({list_width}, {filter_width})'


def _validate_list_keys(lista: dict, where: str = 'list') -> None:
    """Valida chaves de listagem."""
    if lista.get('edit_id_field'):
        raise ValueError(
            f"{where}: 'edit_id_field' foi renomeada para 'edit_id'.")


def _list_slots(lista: dict, pool: list, fonte: dict, parent_entity: str | None = None):
    """SLOTS — resolve `line`/`card`/`hidden` da listagem com ordem declarada.

    Na inversão, o campo **não citado** vai para a linha se for do filho e para
    o card se for do pai (`default_by_entity`). `declared_order` respeita a
    ordem escrita na spec.
    """
    defaults = default_by_entity(lista, fonte, parent_entity)
    return resolve_slots(lista, pool, fonte['pool_entity'],
                         default_by_entity=defaults, declared_order=True)


def default_by_entity(lista: dict, fonte: dict, parent_entity: str | None = None):
    """Slot padrão por entidade na inversão: filho → `line`, pai → `card`."""
    master = fonte.get('master')
    if not master or not parent_entity:
        return {}
    return {master: 'line', parent_entity: 'card'}


def list_max_width(entity_name: str, module_name: str) -> str:
    """Largura final que a listagem do módulo resolve (max_width explícito ou
    padrão `tot_ch`). O container do meio do form segue essa largura quando
    `form.max_width` não é declarado (consome em `core.do_form`)."""
    mod = importlib.import_module(module_name)
    schema = getattr(mod, 'Schema', None) or {}
    page = module_page(mod)
    lista = page_list_cfg(page)
    _validate_list_keys(lista)
    bp_name = module_blueprint(mod).name if module_blueprint(mod) else None
    _ent, _model, _merged, pool, _fonte = _list_pool(lista, schema, module_name,
                                                     entity_name)
    line_fields = _list_slots(lista, pool, _fonte, _fonte.get('parent_entity'))['line']
    edit_endpoint = _resolve_endpoint(lista, 'edit_endpoint', bp_name)
    return resolve_max_width(lista.get('max_width')) or _total_ch(line_fields, edit_endpoint)


def list_fixed_conds(entity_name: str, module_name: str, model=None):
    """Condições fixas (`filter.fixed`) da listagem do módulo, compiladas
    contra `model` (o form usa o próprio). Mesmo pool de `list_max_width`; a
    leitura da prop `filter` passa pelo ponto único (`core.filters.resolve_filter`).

    Guarda de escopo do form (`core.do_form`): abrir um registro que não casa
    com o WHERE fixo da listagem (ex.: um `tipo` errado em `pagar`, ou um
    movimento de transferência numa lista que os exclui) é recusado.
    """
    mod = importlib.import_module(module_name)
    schema = getattr(mod, 'Schema', None) or {}
    page = module_page(mod)
    lista = page_list_cfg(page)
    _ent, _model, _merged, pool, _fonte = _list_pool(lista, schema, module_name,
                                                     entity_name)
    from ajsystem.core.filters import resolve_filter
    return resolve_filter(page_filter_cfg(page), pool=pool,
                          principal=_fonte['pool_entity'],
                          model=model or _model).fixed


def build_tabs(page: dict):
    """Reconstrói a lista de abas + aba ativa a partir do `Page` dict."""
    tabs = []
    props = (page or {}).get('props') or {}
    tab_specs = props.get('tabs')
    list_cfg = props.get('list')
    if not tab_specs:
        tab_specs = {'Dados': {'type': 'List'}}
    for key, cfg in (tab_specs or {}).items():
        cfg = dict(cfg or {})
        ttype = cfg.pop('type', None) or _default_type(key)
        if ttype == 'List' and list_cfg:
            cfg.update(list_cfg)
        tabs.append({
            'id': key,
            'type': ttype,
            'template': cfg.pop('template', None),
            'config': cfg,
        })
    for t in tabs:
        if t['type'] not in TAB_TYPES:
            raise ValueError(f"Page: tipo inválido '{t['type']}' na aba '{t['id']}'")
    if not any(t['type'] == 'Filter' for t in tabs):
        tabs.append({'id': 'Filtros', 'type': 'Filter', 'template': None, 'config': {}})
    return tabs, (tabs[0]['id'] if tabs else '')


def _resolve_endpoint(lista, key, bp_name):
    if key in lista:
        return lista.get(key)
    return f"{bp_name}.form" if bp_name else None



def _infer_edit_id_from_master(child_model, master_name):
    """Infer edit_id como '<rel>.id' a partir da relação filho→master.

    Na inversão, o `edit_id` aponta para o id do pai (master) alcançado
    pela relação do filho. Como `master` já declara a entidade pai, basta
    localizar a relação filho→pai e devolver '<nome_rel>.id'.
    """
    from ajsystem.core.list import _resolve_model
    parent_model = _resolve_model(master_name)
    if parent_model is None:
        return 'id'
    mapper = getattr(child_model, '__mapper__', None)
    if mapper is None:
        return 'id'
    candidatas = [rk for rk, rp in mapper.relationships.items()
                  if rp.mapper.class_ is parent_model]
    if len(candidatas) == 1:
        return f'{candidatas[0]}.id'
    return 'id'


def _inversion_parent_rel_key(lista, merged, child_model, edit_id=None):
    """Nome da relação filho→pai na inversão (`columns`), ou `None`.

    Ex.: no `pagar` invertido (`columns: 'Transacao'`, rota `Previsao`), a
    `Previsao` alcança o pai pela relação `transacao`.

    Quando o filho tem mais de uma N:1 para o pai (ambígua), o prefixo de
    `edit_id` qualificado (`transacao.id` → `transacao`) desempata; sem ele, ou
    sem combinação, levanta `ValueError` nomeando as candidatas.
    """
    if not merged:
        return None
    from ajsystem.core.list import _resolve_model
    child_key = next((k for k in merged
                      if k.lower() == child_model.__name__.lower()), None)
    parent_name = next((k for k in merged if k != child_key), None)
    parent_model = _resolve_model(parent_name) if parent_name else None
    if parent_model is None:
        return None
    mapper = getattr(child_model, '__mapper__', None)
    if mapper is None:
        return None
    candidatas = [rk for rk, rp in mapper.relationships.items()
                  if rp.mapper.class_ is parent_model]
    if not candidatas:
        return None
    if len(candidatas) == 1:
        return candidatas[0]
    # Ambiguidade: desempata pelo prefixo de edit_id qualificado.
    if edit_id:
        prefix = str(edit_id).split('.')[0]
        for cand in candidatas:
            if cand == prefix or cand.startswith(prefix + '_'):
                return cand
    onde = ' e '.join(sorted(candidatas))
    raise ValueError(
        f"list: '{child_model.__name__}' tem mais de uma relação para "
        f"'{parent_model.__name__}' ({onde}) — declare 'edit_id' com o prefixo "
        f"da relação (ex.: 'edit_id: \"{candidatas[0]}.id\"')")


def _inversion_parent_rel(lista, merged, child_model, edit_id=None):
    """Relação filho→pai na inversão (`columns`), ou `None`.

    Ex.: no `pagar` invertido (`columns: 'Transacao'`, rota `Previsao`), a
    `Previsao` alcança o pai pela relação `previsao.transacao`.
    """
    key = _inversion_parent_rel_key(lista, merged, child_model, edit_id)
    return getattr(child_model, key) if key else None


def _inversion_order_attr(lista, merged, child_model, name):
    """Atributo de ordenação/filtro na inversão (`master`).

    `name` pode ser coluna do pai (ex.: no `pagar` invertido, `data`/`tipo`
    são da `Transacao`, não da `Previsao`): então devolve a coluna do pai
    (`Transacao.data`). A query-fonte (`_base_query`) já faz o `JOIN` com o pai
    nesse modo, então a coluna é usável direto em `order_by`/`filter`. Coluna
    do filho → devolve a coluna do filho; inexistente → `None`.

    Só devolve atributo **usável em SQL** (`InstrumentedAttribute` ou hybrid):
    o filho pode ter uma `@property` Python com o mesmo nome de uma coluna do
    pai (`Previsao.status`, `Previsao.saldo`) e ela não serve para `filter`/
    `order_by` (era o `TypeError: '>' not supported between ... 'property'`).
    Nesse caso cai para a coluna do pai. `Previsao.saldo` é hybrid, então ele
    vence e o filtro usa o saldo da previsão (o mesmo da linha).
    """
    def _sql_attr(model, attr_name):
        attr = getattr(model, attr_name, None)
        return attr if attr is not None and hasattr(attr, '__clause_element__') else None

    direct = _sql_attr(child_model, name)
    if direct is not None:
        return direct
    from ajsystem.core.list import _resolve_model
    child_key = next((k for k in merged
                      if k.lower() == child_model.__name__.lower()), None)
    parent_name = next((k for k in merged if k != child_key), None)
    parent_model = _resolve_model(parent_name) if parent_name else None
    return _sql_attr(parent_model, name) if parent_model is not None else None


def _inversion_order_precedence(child_model, principal_model, name):
    """Prioridade de um campo na ordenação da inversão (`master`):
    0 = campo da entidade `master` (filho); 1 = campo do pai; 2 = outro.

    Particionamento estável: dentro de cada grupo preserva-se a ordem
    declarada no `order`."""
    if getattr(child_model, name, None) is not None:
        return 0
    if getattr(principal_model, name, None) is not None:
        return 1
    return 2


def _pool_entity(lista, entity_name):
    """A entidade que `columns` nomeia, ou `None`.

    É a que um nome CRU de slot resolve: `columns: 'Transferencia'` numa lista
    invertida (`master: 'Movimento'`) significa que a lista é sobre a
    Transferência, então `hidden: ['documento']` é o dela — mesmo tendo
    `documento` nas duas pontas. Só `columns` string conta: `fields` é alias
    legado e pode ser lista, e `columns` lista/`query` não nomeia entidade
    alguma.
    """
    return entity_name if isinstance(lista.get('columns'), str) else None


def _inversion_entity(lista: dict, entity_name: str) -> str | None:
    """A entidade que `columns` nomeia, quando string: é a entidade das linhas.

    `columns` string numa listagem sem `master` significa inversão: o filho é a
    entidade das linhas, a entidade da rota é o pai. Quando `columns` é o nome
    da própria entidade da rota, não há inversão — é apenas expansão dos
    campos dela. Retorna `None` quando não há inversão (`columns` lista/query/
    pivot, ou string igual a `entity_name`)."""
    columns = lista.get('columns')
    if isinstance(columns, str) and columns != entity_name:
        return columns
    return None


def _list_pool(lista, schema, module_name, entity_name):
    """POOL — os fields que a listagem considera, antes dos slots.

    `columns` é quem decide **quem existe** na listagem (entidade = expansão,
    lista = autoritativa, query dict = fonte do `qrun`; com inversão de `columns`
    string, as duas entidades da inversão); os slots `line`/`card`/`hidden`
    só distribuem o que está aqui. Cada field sai com `_entity` preenchido — é
    contra isso que um nome de slot é resolvido, e é por isso que este é o
    construtor **único** do pool: `list_max_width` (o `do_form` pede a largura
    da listagem da rota) monta o mesmo pool que a listagem, inversão incluída.

    Na inversão (`columns` string = entidade das linhas), o pool é
    `_tagged(filho) + _tagged(pai)`: filho primeiro (ordem das colunas da linha)
    e o pai depois.

    `fonte['pool_entity']` é a entidade que `columns` nomeia (a que um nome cru
    de slot resolve) — `None` quando `columns` é lista ou fonte `query`.
    `fonte['master']` é o nome da entidade da linha na inversão, quando há.
    `fonte['parent_entity']` é a entidade da rota (o pai) na inversão.

    Devolve `(entity_name, model, merged, pool, fonte)`; `fonte` traz também o
    que a fonte `query` acrescenta (`is_query`/`colspec`/`colorder`), para o
    chamador não ter que reparsear `columns`.
    """
    from ajsystem.defs.qspec import (
        is_pivot_dict as _is_p, is_query_dict as _is_q,
    )
    _validate_list_keys(lista)
    _colspec = lista.get('columns', lista.get('fields', entity_name))
    # Forma enxuta fonte+ordem: query/pivot dict como item da lista; as strings
    # dão recorte/ordem autoritativos. No máximo UMA fonte por lista.
    _colorder = None
    _is_query = _is_q(_colspec)
    _is_pivot = _is_p(_colspec)
    if isinstance(_colspec, list):
        _items = list(_colspec)
        _qs = [it for it in _items if _is_q(it)]
        _pv = [it for it in _items if _is_p(it)]
        if len(_qs) + len(_pv) > 1:
            raise ValueError("list: no máximo uma fonte em columns (query ou pivot)")
        if _qs:
            _colspec = _qs[0]
            _is_query = True
            _colorder = []
            for it in _items:
                if _is_q(it):
                    continue
                if not isinstance(it, str):
                    raise ValueError(f"list: com query, item deve ser str (campo), veio {type(it).__name__}")
                _colorder.append(it)
        elif _pv:
            if len(_items) > 1:
                raise ValueError(
                    "list: com pivot, columns deve conter só o pivot "
                    "(recorte de colunas geradas é fase 2; use line/hidden)")
            _colspec = _pv[0]
            _is_pivot = True
    if _is_query and isinstance(_colspec.get('from'), str):
        entity_name = _colspec['from']
    inputs = _camadas_inputs(module_name)
    master_name = None  # `master` foi removida (falha explícita acima)

    if _is_pivot:
        if master_name:
            raise ValueError("list: 'master' não suporta fonte pivot")
        from ajsystem.defs.qspec import parse_pivot as _pp
        _pspec = _pp(_colspec)
        _src = _pspec.src
        if isinstance(_src, str):
            entity_name = _src
        elif isinstance(_src, dict):
            entity_name = _src.get('from')
            if isinstance(entity_name, (list, tuple)):
                entity_name = entity_name[0] if entity_name else None
        if not isinstance(entity_name, str) or not entity_name:
            raise ValueError("list: pivot exige uma entidade em 'src' (str ou 'from')")
        model = _resolve_model(entity_name)
        merged = resolve_entity_fields(schema, model, entity_name)
        # O pool devolvido aqui é o da ORIGEM: é ele que o painel de filtro
        # usa e que serve de fallback de largura. As colunas geradas só
        # existem depois de executar o pivot (`do_list_normal`).
        pool = resolve_column_configs(merged, entity_name, principal=merged,
                                      inputs=inputs)
        for f in pool:
            f._entity = entity_name
        return entity_name, model, merged, pool, {
            'is_query': False, 'is_pivot': True, 'pivotspec': _pspec,
            'colspec': _colspec, 'colorder': None, 'base_pool': pool,
            'pool_entity': entity_name, 'master': None,
        }

    if isinstance(_colspec, str):
        # `columns` string = entidade das linhas (filho na inversão). A entidade
        # da rota é o pai. Só entra na inversão quando `columns` != entity_name;
        # quando é igual, é uma listagem comum da própria entidade.
        if _colspec != entity_name:
            child_name = _colspec
            parent_name = entity_name
            parent_model = _resolve_model(parent_name)
            model = _resolve_model(child_name)
            merged = {
                child_name: resolve_entity_fields(schema, model, child_name),
                parent_name: resolve_entity_fields(schema, parent_model, parent_name),
            }

            def _tagged(ent):
                cfgs = resolve_column_configs(merged, ent, principal=merged,
                                              inputs=inputs)
                for f in cfgs:
                    f._entity = ent
                return cfgs

            pool = _tagged(child_name) + _tagged(parent_name)
            return entity_name, model, merged, pool, {
                'is_query': False, 'is_pivot': False, 'colspec': _colspec,
                'colorder': None, 'base_pool': None,
                'pool_entity': child_name, 'master': child_name,
                'parent_model': parent_model, 'parent_entity': parent_name,
            }

    model = _resolve_model(entity_name)
    # RS/RE — camadas Schema e Entity sobre os fields da entidade, via
    # `core.resolve.apply_field_layers` (Schema vence conflitos).
    merged = resolve_entity_fields(schema, model, entity_name)
    if _is_query:
        from ajsystem.defs.qspec import parse_select as _ps
        from ajsystem.core.resolve import query_select_layer as _rq
        _qentries = list(_ps(_colspec.get('select')))
        # RQ — camada da fonte query sobre a Entity/Schema (query vence,
        # destilando `calc` quando a query computa; label/width/align da query).
        _merged_q = _rq(_qentries, merged)
        shown = [e.name for e in _qentries]
        if _colorder:
            _sel = {e.name for e in _qentries}
            for _fn in _colorder:
                if _fn not in _sel:
                    raise ValueError(f"list: field '{_fn}' não está no select da query")
            shown = list(_colorder)
        pool = resolve_column_configs(_merged_q, shown, principal=_merged_q, inputs=inputs)
    else:
        pool = resolve_column_configs(merged, _colspec, principal=merged, inputs=inputs)
    for f in pool:
        f._entity = entity_name
    return entity_name, model, merged, pool, {
        'is_query': _is_query, 'is_pivot': False, 'colspec': _colspec,
        'colorder': _colorder, 'base_pool': None,
        'pool_entity': _pool_entity(lista, entity_name), 'master': None,
        'parent_entity': None,
    }


def _guard_pivot_list(lista, fonte, entity_name):
    """Restrições da listagem com fonte pivot (v1: somente leitura).

    Não há linha de origem para editar (as linhas são grupos), e a inversão
    `columns`/`detail` pressupõe um registro do model.
    """
    if fonte.get('master'):
        raise ValueError("list: 'master' não suporta fonte pivot")
    if 'detail' in lista:
        raise ValueError(
            f"list '{entity_name}': 'detail' não suporta fonte pivot")
    if lista.get('field_id') or lista.get('edit_id_field') or lista.get('edit_id'):
        raise ValueError(
            f"list '{entity_name}': pivot é somente leitura "
            "(sem field_id/edit_id/edit_id_field)")
    if lista.get('edit_endpoint'):
        raise ValueError(
            f"list '{entity_name}': pivot é somente leitura (sem edit_endpoint)")


def _camadas_botoes(module_name):
    """Catálogos de botão da listagem: o do app e o do módulo da rota.

    A listagem resolve botão pelo mesmo caminho do form, então precisa das mesmas
    duas camadas — sem elas, um nome declarado em `app.extends.buttons.Buttons` ou no
    `Buttons` do módulo não resolveria aqui (e a página de listagem quebraria
    num botão que a de form mostra).
    """
    from ajsystem.defs.buttons import module_buttons
    botoes = current_app.extensions.get('botoes')
    page = {}
    if module_name:
        try:
            page = module_buttons(importlib.import_module(module_name))
        except ImportError:
            page = {}
    return botoes, page


def _camadas_inputs(module_name):
    """Camadas de input da listagem: o do app e o do módulo da rota.

    Gêmeo de `_camadas_botoes`. Uma coluna da listagem é um `Field` como outro
    qualquer, e o `input` decide como a célula é impressa (`inp.number`,
    `inp.boolean`, `inp.filter_kind`) e filtrada — então a listagem precisa das
    mesmas duas camadas, senão a mesma entidade mostraria coluna de um jeito no
    form e de outro na grade.
    """
    from ajsystem.defs.inputs import module_inputs
    inputs = current_app.extensions.get('inputs')
    page = {}
    if module_name:
        try:
            page = module_inputs(importlib.import_module(module_name))
        except ImportError:
            page = {}
    return inputs, page


def do_list(entity_name: str, module_name: str, data=None, **extra):
    """Entrada da listagem — roteia para `do_list_master` (linhas de outra
    entidade via `columns`) ou `do_list_normal` (linhas da própria entidade)."""
    mod = importlib.import_module(module_name)
    page = module_page(mod)
    lista = page_list_cfg(page)
    if _inversion_entity(lista, entity_name):
        return do_list_master(entity_name, module_name, data=data, **extra)
    return do_list_normal(entity_name, module_name, data=data, **extra)


def do_list_normal(entity_name: str, module_name: str, data=None, **extra):
    """Listagem comum — fluxo original intacto (sem inversão `master`)."""
    mod = importlib.import_module(module_name)
    schema = getattr(mod, 'Schema', None) or {}
    page = module_page(mod)
    tabs, active_tab = build_tabs(page)
    lista = page_list_cfg(page)
    _validate_list_keys(lista)
    bp_name = module_blueprint(mod).name if module_blueprint(mod) else None

    # POOL (quem existe) → SLOTS (onde cada um vai). Ver `_list_pool`.
    entity_name, model, merged, pool, fonte = _list_pool(lista, schema,
                                                         module_name, entity_name)
    _is_query, _is_pivot = fonte['is_query'], fonte.get('is_pivot', False)
    _colspec = fonte['colspec']
    if _is_pivot:
        _guard_pivot_list(lista, fonte, entity_name)

    # Campo de impressão com escolha ativo (marcador `_r`): o parâmetro que o
    # relatório injetou na URL não deve virar filtro da listagem, senão o filtro
    # de impressão persistiria na lista ao "Voltar". Resolve-se a listagem sem
    # esse campo.
    from ajsystem.core import do_report as _drp
    rid = request.args.get('_r')
    _print_field = _drp._print_field_of(rid) if rid else None
    _fargs = {k: v for k, v in request.args.items(multi=True) if k != _print_field}

    # Fonte pivot: o painel filtra a ORIGEM (tipo/data/conta...), não as
    # colunas geradas — elas só existem depois de executar o pivot. A execução
    # acontece aqui, antes dos slots, para o pool já conter linhas+colunas.
    if _is_pivot:
        from ajsystem.core.pivot import pivot_layer, run_pivot
        _base_pool = fonte['base_pool']
        _rf = resolve_filter(
            page_filter_cfg(page), pool=_base_pool,
            principal=fonte['pool_entity'], model=model,
            fields=_base_pool, request_args=_fargs)
        _extra_conds = list(_rf.fixed)
        if _rf.filter_cond is not None:
            _extra_conds.append(_rf.filter_cond)
        _pres = run_pivot(model, _colspec, entity_cfg=merged,
                          extra_conditions=_extra_conds)
        if data is None:
            data = _pres.rows
        _layer = pivot_layer(_pres, merged)
        _shown = ([ax.name for ax in _pres.lines]
                  + [c.name for c in _pres.columns])
        pool = resolve_column_configs(
            _layer, _shown, principal=_layer,
            inputs=_camadas_inputs(module_name))
        for f in pool:
            f._entity = fonte['pool_entity']

    slots = _list_slots(lista, pool, fonte)
    line_fields, cardonly_fields = slots['line'], slots['card']

    all_fields = line_fields + cardonly_fields
    stored_cols = {c.name for c in model.__table__.columns}
    for f in all_fields:
        f.stored = f.name in stored_cols
    fields_master = list(range(1, len(line_fields) + 1))

    if _is_pivot:
        _fid = None
        edit_endpoint = None
    elif _is_query:
        _fid = 'id'
        edit_endpoint = _resolve_endpoint(lista, 'edit_endpoint', bp_name)
    else:
        _fid = None
        edit_endpoint = _resolve_endpoint(lista, 'edit_endpoint', bp_name)

    from ajsystem.defs.data import resolve_lookup
    for f in line_fields + cardonly_fields:
        resolved = resolve_lookup(f, model)
        if resolved is not None:
            f.lookup = resolved

    list_obj = List(
        fields=all_fields,
        fields_master=fields_master,
        edit_endpoint=edit_endpoint,
        edit_id='id',
        template=lista.get('template'),
        card_idx=(list(range(len(line_fields) + 1, len(all_fields) + 1))
                  if len(all_fields) > len(line_fields) else None),
        buttons=lista.get('buttons'),
    )
    buttons = list_obj.resolve_buttons(bp_name, *_camadas_botoes(module_name))

    report_entries = {}
    if any(t['type'] == 'Report' for t in tabs):
        report_entries = _resolve_report_entries(page, schema, module_name,
                                                entity_name)

    detail_fields = None
    detail_data = None
    if 'detail' in lista:
        _dspec = lista['detail']
        if isinstance(_dspec, dict):
            _dfields, detail_data = _dspec.get('fields', []), _dspec.get('data')
        else:
            _dfields, detail_data = _dspec, entity_name.lower() + '_items'
        if detail_data:
            _rel = getattr(model, detail_data, None)
            try:
                _child = _rel.property.mapper.class_ if _rel is not None else None
            except Exception:
                _child = None
            if _child is not None:
                _cmerged = resolve_entity_fields(schema, _child, _child.__name__)
            else:
                _cmerged = merged
            detail_fields = resolve_column_configs(_cmerged, _dfields, principal=_cmerged, inputs=_camadas_inputs(module_name))
        else:
            detail_fields = resolve_column_configs(merged, _dfields, principal=merged, inputs=_camadas_inputs(module_name))
        list_obj.detail_data = detail_data

    # Campo de impressão com escolha ativo — resolvido antes do pivot/filtro
    # (ver acima); aqui só resta o filtro do fluxo comum.
    if _is_pivot:
        filter_config = _rf.panel
        initial_filters, default_filters = _rf.initial, _rf.default_filters
        active = _rf.active
    else:
        _rf = resolve_filter(
            page_filter_cfg(page), pool=pool, principal=fonte['pool_entity'],
            model=model, fields=list_obj.fields, request_args=_fargs)
        filter_config = _rf.panel
        initial_filters, default_filters = _rf.initial, _rf.default_filters
        active = _rf.active
    page_max_width = _list_page_width(
        lista, list_obj, tabs, _rf.max_width if filter_config else None)

    def _base_query():
        q = model.query
        if _rf.fixed:
            q = q.filter(*_rf.fixed)
        if _rf.filter_cond is not None:
            q = q.filter(_rf.filter_cond)
        return q

    if data is None and _is_query:
        from ajsystem.core.qrun import run_query as _rq
        _extra_conds = list(_rf.fixed)
        if _rf.filter_cond is not None:
            _extra_conds.append(_rf.filter_cond)
        data = _rq(model, _colspec, entity_cfg=merged,
                   extra_conditions=_extra_conds)
    if data is None and not _is_pivot:
        ordering = lista.get('order', []) or lista.get('ordering', [])
        if isinstance(ordering, str):
            ordering = [ordering]
        if ordering:
            data = _base_query().order_by(*[getattr(model, c) for c in ordering]).all()
        else:
            data = _base_query().all()

    calc_field = next((f for f in line_fields if callable(getattr(f, 'calc', None))), None)
    if calc_field and data and not _is_query and not _is_pivot:
        data = sorted(data, key=calc_field.calc)

    ctx = build_field_context(list_obj.fields)

    # Impressão com escolha (render interno): se a request traz o marcador
    # `_r` de um modal de `filter_select`, gera o fragmento do PDF aqui e o
    # injeta automaticamente no load (reportRender), sem rota nova. O botão de
    # impressão continua sempre devolvendo o modal, permitindo reimprimir com
    # outro critério.
    auto_report = None
    if rid:
        from ajsystem.core import do_report as _dr
        auto_report = _dr._consume_pending_print(rid)

    title = lista.get('title') or _auto_label(entity_name)
    new_endpoint = _resolve_endpoint(lista, 'new_endpoint', bp_name)
    new_url = url_for(new_endpoint) if new_endpoint else None
    new_label = lista.get('new_label') or None

    template = (lista.get('template') or "pages/list.html")

    return render_template(
        template,
        entity_name=entity_name,
        list_page=True,
        TABS=tabs,
        active_tab=active_tab,
        LIST=list_obj,
        data=data,
        active_filters=active,
        initial_filters=initial_filters,
        default_filters=default_filters,
        default_on=_rf.default_on,
        filter_max_width=_rf.max_width,
        FILTERS=filter_config,
        REPORTS=report_entries,
        page_scripts=page_scripts(page),
        ctx=ctx,
        titulo=title,
        new_url=new_url,
        new_label=new_label,
        max_width=page_max_width,
        detail_fields=detail_fields,
        detail_data=detail_data,
        cardonly_fields=cardonly_fields,
        buttons=buttons,
        auto_report=auto_report,
        **extra,
    )


def do_list_master(entity_name: str, module_name: str, data=None, **extra):
    """Listagem invertida (`columns`) — fluxo próprio, separado da listagem comum.

    As linhas passam a ser os registros do filho (entidade de `columns`);
    a entidade da rota (`entity_name`) é o pai alcançado por relação. Regras da
    inversão:
      - colunas: começam pelos campos da entidade `columns`, seguidas dos campos
        do pai (é o pool que os slots `line`/`card`/`hidden` distribuem);
      - ordenação: campos da entidade `columns` primeiro, depois os do pai
        (requer `JOIN` com o pai para alcançar as colunas dele);
      - filtros continuam pelos fields do pool (resolvendo colunas do pai
        pela relação).
    """
    mod = importlib.import_module(module_name)
    schema = getattr(mod, 'Schema', None) or {}
    page = module_page(mod)
    tabs, active_tab = build_tabs(page)
    lista = page_list_cfg(page)
    bp_name = module_blueprint(mod).name if module_blueprint(mod) else None

    # POOL (filho primeiro, depois o pai) + merged das duas — mesmo caminho do
    # `do_list_normal`, para que `list_max_width` (que só o pai) e a listagem
    # resolvam exatamente o mesmo conjunto de fields.
    entity_name, model, merged, pool, fonte = _list_pool(lista, schema,
                                                         module_name, entity_name)
    principal_model = fonte['parent_model']
    parent_entity = fonte.get('parent_entity')

    # `master` é obrigatório na inversão: declara a entidade pai.
    props = page.get('props') or {}
    master = props.get('master') if isinstance(props, dict) else None
    if not master:
        raise ValueError(
            f"list '{entity_name}': inversão detectada "
            f"(columns='{fonte.get('pool_entity')}' != entity_name='{entity_name}') "
            f"mas 'master' não declarado em Page.props. "
            f"Declare 'props.master' com a entidade mestre "
            f"(ex.: 'props.master': 'Transacao').")

    # Infere edit_id da relação filho→master: '<rel>.id'
    edit_id = _infer_edit_id_from_master(model, master)

    slots = _list_slots(lista, pool, fonte, parent_entity)
    line_fields, cardonly_fields = slots['line'], slots['card']

    all_fields = line_fields + cardonly_fields
    stored_cols = {c.name for c in model.__table__.columns}
    for f in all_fields:
        f.stored = f.name in stored_cols
    fields_master = list(range(1, len(line_fields) + 1))

    # `prio`: posição ordinal dos campos da linha (filho e/ou pai).
    # Item pode ser:
    #   - str: 'campo' ou 'Entidade.campo' (vai para line, sem posição fixa)
    #   - tuple: (posicao, campo) — posicao 1-based na linha
    # Label/width/align continuam vindo da Entity/Schema; prio só posiciona.
    _prio = lista.get('prio')
    if _prio:
        by_id = {id(f): f for f in all_fields}
        prio_map = {}   # posicao (1-based) -> id do field
        prio_free = []  # campos de prio sem posicao fixa
        for entry in _prio:
            if isinstance(entry, tuple):
                pos, field_name = entry
            else:
                field_name = entry
                pos = None
            # Nome pode vir qualificado: 'Entidade.campo' ou cru 'campo'
            if isinstance(field_name, str) and '.' in field_name:
                ent_name, field_name = field_name.split('.', 1)
            else:
                ent_name = None
            matches = [f for f in all_fields
                       if f.name == field_name
                       and (ent_name is None
                            or getattr(f, '_entity', None) == ent_name)]
            if not matches:
                raise ValueError(
                    f"list '{entity_name}': 'prio' campo '{field_name}' "
                    f"não encontrado no pool da listagem.")
            f = matches[0]
            f._slot = 'line'
            if pos is not None:
                prio_map[int(pos)] = id(f)
            else:
                prio_free.append(id(f))

        # Monta linha final respeitando posições fixas de prio
        n_line = len(line_fields)
        saida = [None] * n_line
        usados = set()
        # Coloca campos com posição fixa (ignora posicoes fora do range)
        for pos, fid in prio_map.items():
            idx = pos - 1
            if 0 <= idx < n_line and saida[idx] is None:
                saida[idx] = by_id.get(fid)
                usados.add(fid)
        # Campos de prio sem posicao fixa preenchem espacos vagos em ordem
        for fid in prio_free:
            f = by_id.get(fid)
            if f is None or id(f) in usados:
                continue
            for i in range(n_line):
                if saida[i] is None:
                    saida[i] = f
                    usados.add(id(f))
                    break
        # Demais campos da linha preenchem espacos vagos restantes
        for f in line_fields:
            if id(f) in usados:
                continue
            for i in range(n_line):
                if saida[i] is None:
                    saida[i] = f
                    usados.add(id(f))
                    break
        line_fields = [f for f in saida if f is not None]
        # Remove de cardonly os campos que prio moveu para a line (evita duplicacao)
        prio_ids_usados = set(usados)
        cardonly_fields = [f for f in cardonly_fields if id(f) not in prio_ids_usados]
        all_fields = line_fields + cardonly_fields
        fields_master = list(range(1, len(line_fields) + 1))

    # Campos do pai (entidade da rota) vivem no registro relacionado da linha:
    # o template resolve o valor por `card_path` (`rel.campo`) e os lookups
    # desses campos também precisam do caminho através da relação (`rel×path`).
    parent_rel = _inversion_parent_rel_key(lista, merged, model, edit_id)
    for f in line_fields + cardonly_fields:
        if getattr(f, '_entity', None) == entity_name and parent_rel:
            f.card_path = f'{parent_rel}.{f.name}'
            if f.lookup and isinstance(f.lookup, dict) and f.lookup.get('path'):
                f.lookup['path'] = f'{parent_rel}.{f.lookup["path"]}'

    edit_endpoint = _resolve_endpoint(lista, 'edit_endpoint', bp_name)

    from ajsystem.defs.data import resolve_lookup
    for f in line_fields + cardonly_fields:
        source = principal_model if getattr(f, '_entity', None) == entity_name else model
        resolved = resolve_lookup(f, source)
        if resolved is not None:
            f.lookup = resolved
            if getattr(f, '_entity', None) == entity_name and parent_rel:
                f.lookup['path'] = f'{parent_rel}.{f.lookup["path"]}'

    list_obj = List(
        fields=all_fields,
        fields_master=fields_master,
        edit_endpoint=edit_endpoint,
        edit_id=edit_id,
        template=lista.get('template'),
        card_idx=(list(range(len(line_fields) + 1, len(all_fields) + 1))
                  if len(all_fields) > len(line_fields) else None),
        buttons=lista.get('buttons'),
    )
    buttons = list_obj.resolve_buttons(bp_name, *_camadas_botoes(module_name))

    report_entries = {}
    if any(t['type'] == 'Report' for t in tabs):
        report_entries = _resolve_report_entries(page, schema, module_name,
                                                entity_name)

    detail_fields = None
    detail_data = None
    if 'detail' in lista:
        _dspec = lista['detail']
        if isinstance(_dspec, dict):
            _dfields, detail_data = _dspec.get('fields', []), _dspec.get('data')
        else:
            _dfields, detail_data = _dspec, entity_name.lower() + '_items'
        if detail_data:
            _rel = getattr(model, detail_data, None)
            try:
                _child = _rel.property.mapper.class_ if _rel is not None else None
            except Exception:
                _child = None
            if _child is not None:
                _cmerged = resolve_entity_fields(schema, _child, _child.__name__)
            else:
                _cmerged = merged
            detail_fields = resolve_column_configs(_cmerged, _dfields, principal=_cmerged, inputs=_camadas_inputs(module_name))
        else:
            detail_fields = resolve_column_configs(merged, _dfields, principal=merged, inputs=_camadas_inputs(module_name))
        list_obj.detail_data = detail_data

    # Campo de impressão com escolha ativo (marcador `_r`): o parâmetro que o
    # relatório injetou na URL não deve virar filtro da listagem, senão o filtro
    # de impressão persistiria na lista ao "Voltar". Resolve-se a listagem sem
    # esse campo.
    from ajsystem.core import do_report as _drp
    rid = request.args.get('_r')
    _print_field = _drp._print_field_of(rid) if rid else None
    _fargs = {k: v for k, v in request.args.items(multi=True) if k != _print_field}

    _inversion_resolver = lambda m, n: _inversion_order_attr(lista, merged, m, n)
    _rf = resolve_filter(
        page_filter_cfg(page), pool=pool, principal=fonte['pool_entity'],
        model=model, attr_resolver=_inversion_resolver,
        fields=list_obj.fields, request_args=_fargs)
    filter_config = _rf.panel
    initial_filters, default_filters = _rf.initial, _rf.default_filters
    active = _rf.active
    page_max_width = _list_page_width(
        lista, list_obj, tabs, _rf.max_width if filter_config else None)
    _parent_rel = _inversion_parent_rel(lista, merged, model, edit_id)

    def _base_query():
        q = model.query
        if _parent_rel is not None:
            q = q.join(_parent_rel)
        if _rf.fixed:
            q = q.filter(*_rf.fixed)
        if _rf.filter_cond is not None:
            q = q.filter(_rf.filter_cond)
        return q

    def _master_ordering():
        order = lista.get('order', []) or lista.get('ordering', [])
        if isinstance(order, str):
            order = [order]
        return sorted(order, key=lambda c: _inversion_order_precedence(model, principal_model, c))

    if data is None:
        ordering = _master_ordering()
        if ordering:
            data = _base_query().order_by(*[_inversion_order_attr(lista, merged, model, c) for c in ordering]).all()
        else:
            data = _base_query().all()

    calc_field = next((f for f in line_fields if callable(getattr(f, 'calc', None))), None)
    if calc_field and data:
        data = sorted(data, key=calc_field.calc)

    ctx = build_field_context(list_obj.fields)

    # Impressão com escolha (render interno): se a request traz o marcador
    # `_r` de um modal de `filter_select`, gera o fragmento do PDF aqui e o
    # injeta automaticamente no load (reportRender), sem rota nova. O botão de
    # impressão continua sempre devolvendo o modal, permitindo reimprimir com
    # outro critério.
    auto_report = None
    if rid:
        from ajsystem.core import do_report as _dr
        auto_report = _dr._consume_pending_print(rid)

    title = lista.get('title') or _auto_label(entity_name)
    new_endpoint = _resolve_endpoint(lista, 'new_endpoint', bp_name)
    new_url = url_for(new_endpoint) if new_endpoint else None
    new_label = lista.get('new_label') or None

    template = (lista.get('template') or "pages/list.html")

    return render_template(
        template,
        entity_name=entity_name,
        list_page=True,
        TABS=tabs,
        active_tab=active_tab,
        LIST=list_obj,
        data=data,
        active_filters=active,
        initial_filters=initial_filters,
        default_filters=default_filters,
        default_on=_rf.default_on,
        filter_max_width=_rf.max_width,
        FILTERS=filter_config,
        REPORTS=report_entries,
        page_scripts=page_scripts(page),
        ctx=ctx,
        titulo=title,
        new_url=new_url,
        new_label=new_label,
        max_width=page_max_width,
        detail_fields=detail_fields,
        detail_data=detail_data,
        cardonly_fields=cardonly_fields,
        buttons=buttons,
        auto_report=auto_report,
        **extra,
    )


def _report_slug(title):
    """Slug de URL da entrada (`Gerar` envia `rp=<slug>`)."""
    import re
    slug = re.sub(r'[^a-z0-9]+', '-', normalizar_slug(title)).strip('-')
    return slug or 'relatorio'


def _report_filter_pairs(cfg, where):
    """Normaliza `props.report[..].filter` em `[(entidade|None, campo, op)]`.

    Formas aceitas: a família fieldspec (`'campo'`, lista, `{'Ent': [...]}`,
    tudo com `=`) ou o dict `{campo: op}` com operador em `REPORT_OPS`.
    """
    from ajsystem.core.resolve import slot_spec_items
    spec = cfg.get('filter')
    if not spec:
        return []
    if isinstance(spec, (str, list, tuple)):
        return [(ent, name, '=') for ent, name in
                slot_spec_items(spec, 'filter', where)]
    if not isinstance(spec, dict):
        raise TypeError(f"{where}.filter: esperava str, lista ou dict; veio "
                        f"{type(spec).__name__}")
    out = []
    for key, val in spec.items():
        if isinstance(val, str):
            if val not in REPORT_OPS:
                raise ValueError(
                    f"{where}.filter[{key!r}]: operador {val!r} inválido — "
                    f"use {', '.join(REPORT_OPS)}")
            out.extend((ent, name, val, None) for ent, name in
                       slot_spec_items([key], 'filter', where))
        elif isinstance(val, dict):
            op = val.get('op', '=')
            if op not in REPORT_OPS:
                raise ValueError(
                    f"{where}.filter[{key!r}]: operador {op!r} inválido — "
                    f"use {', '.join(REPORT_OPS)}")
            default = val.get('default')
            out.extend((ent, name, op, default) for ent, name in
                       slot_spec_items([key], 'filter', where))
        elif isinstance(val, (list, tuple)) and len(val) == 2 \
                and isinstance(val[0], str) and val[0] in REPORT_OPS:
            # Tupla (operador, default): ex. ('<', lastDay(TODAY()))
            op = val[0]
            default = val[1]
            out.extend((ent, name, op, default) for ent, name in
                       slot_spec_items([key], 'filter', where))
        elif isinstance(val, (list, tuple)):
            # fieldspec agrupado (`{'Entidade': [...]}`) — sem operador, `=`.
            out.extend((ent, name, '=', None) for ent, name in
                       slot_spec_items({key: val}, 'filter', where))
        else:
            raise TypeError(
                f"{where}.filter[{key!r}]: esperava operador (str) ou dict "
                f"{{op, default}}; veio {type(val).__name__}")
    return out


def _resolve_report_entries(page, schema, module_name, entity_name):
    """Resolve `props.report` para a aba Relatórios (`filter` → pool)."""
    from ajsystem.core.resolve import _pool_entities, _slot_match
    from ajsystem.core.list import infer_filter_type, field_filter_options
    from ajsystem.defs.data import resolve_lookup
    report_cfg = page_report_cfg(page)
    if not report_cfg:
        return {}
    lista = page_list_cfg(page)
    _ent, model, merged, pool, fonte = _list_pool(lista, schema, module_name,
                                                  entity_name)
    principal = fonte.get('pool_entity')
    entities = _pool_entities(pool)
    entries = {}
    seen_slugs = {}
    for title, cfg in report_cfg.items():
        where = f"Page.props.report[{title!r}]"
        if not isinstance(cfg, dict):
            raise TypeError(f"{where}: deve ser dict, veio {type(cfg).__name__}")
        if 'report' not in cfg:
            current_app.logger.warning(
                f"{where}: chave 'report' ausente — entrada ignorada para o painel")
            # Ainda assim adicionamos a entrada ao REPORTS para o painel ser
            # construído; o botão "GERAR" ficará disabled até que se adicione o spec.
            cfg['report'] = None
        slug = _report_slug(title)
        if slug in seen_slugs:
            raise ValueError(f"{where}: título gera o mesmo slug "
                             f"{slug!r} de {seen_slugs[slug]!r}")
        seen_slugs[slug] = title
        items = []
        for ent, name, op, default in _report_filter_pairs(cfg, where):
            hits = _slot_match(pool, entities, ent, name, 'filter', principal,
                               where)
            for f in hits:
                ftype = infer_filter_type(f)
                if not ftype:
                    raise ValueError(
                        f"{where}.filter[{f.name!r}]: campo não é filtrável "
                        f"(tipo {getattr(f, '_type', '?')})")
                if op not in _REPORT_OPS_BY_TYPE[ftype]:
                    raise ValueError(
                        f"{where}.filter[{f.name!r}]: operador {op!r} inválido "
                        f"para {ftype} — use "
                        f"{', '.join(_REPORT_OPS_BY_TYPE[ftype])}")
                sql_op = op
                if ftype == 'date' and op in ('>', '<'):
                    sql_op = '>=' if op == '>' else '<='
                item = {
                    'name': f.name,
                    'label': getattr(f, 'display_label', None) or f.name,
                    'type': ftype,
                    'op': op,
                    'sql_op': sql_op,
                    'between': op == '<>',
                    'mode_label': _REPORT_OP_LABEL[ftype][op],
                }
                if default is not None:
                    item['default'] = default
                if ftype in ('select', 'checklist', 'boolean'):
                    # O pool não resolve `lookup` (só os slots da listagem o
                    # fazem); sem `target` o FK não tem options no form.
                    if getattr(f, 'lookup', None) is not None:
                        ent_name = getattr(f, '_entity', None) or entity_name
                        resolved = resolve_lookup(f, _resolve_model(ent_name))
                        if resolved is not None:
                            f.lookup = resolved
                    opts = field_filter_options(f)
                    if opts:
                        item['options'] = opts
                items.append(item)
        # Variants: {'0:por Cliente': ['conta_id', 'vencimento', 'syn'], ...}
        variants = {}
        for _vkey, _vval in (cfg.get('variants') or {}).items():
            if isinstance(_vkey, str) and ':' in _vkey:
                _idx_s, _label = _vkey.split(':', 1)
                try:
                    _idx = int(_idx_s)
                except ValueError:
                    _idx = _label
            else:
                _idx, _label = _vkey, _vkey
            _vlist = list(_vval or [])
            variants[_idx] = {
                'label': _label,
                'fields': [v for v in _vlist if v != 'syn'],
                'syn': 'syn' in _vlist,
            }
        # Sintético só aparece quando o layout da tabela declara 'syn'.
        _has_syn = False
        _rep = cfg.get('report')
        if isinstance(_rep, dict):
            _body = _rep.get('body')
            if isinstance(_body, dict):
                _table = _body.get('table')
                if isinstance(_table, dict):
                    from ajsystem.defs.report import table_has_syn
                    _has_syn = table_has_syn(_table)
        entries[title] = {'slug': slug, 'title': title,
                          'report': cfg['report'], 'fields': items,
                          'variants': variants,
                          'has_syn': _has_syn}
    return entries


def report_filter_from_args(entry, args):
    """Args do form da aba Relatórios → spec literal (gramática compartilhada).

    Só os campos declarados na entrada são lidos; vazio ignora a folha. `<>`
    vira duas folhas (>=/<=) com as partes preenchidas; `like` ganha `%...%`;
    select/boolean/checklist viram `in`/`not in`.
    """
    from datetime import date as _date

    def filled(v):
        return v is not None and str(v).strip() != ''

    def typed(f, v):
        if f['type'] == 'date':
            s = str(v).strip()
            try:
                return _date.fromisoformat(s)
            except (TypeError, ValueError):
                pass
            # Aceita formato brasileiro dd/mm/aaaa
            try:
                parts = s.split('/')
                if len(parts) == 3:
                    return _date(int(parts[2]), int(parts[1]), int(parts[0]))
            except (TypeError, ValueError):
                pass
            return v
        return v

    out = []
    for f in entry['fields']:
        name, op = f['name'], f['op']
        if f['between']:
            suf = (('_from', '_to') if f['type'] == 'date'
                   else ('_val1', '_val2'))
            lo, hi = args.get(name + suf[0]), args.get(name + suf[1])
            if filled(lo):
                out.append({name: ('>=', typed(f, lo))})
            if filled(hi):
                out.append({name: ('<=', typed(f, hi))})
            continue
        if f['type'] == 'checklist':
            vals = [v for v in args.getlist(name) if filled(v)]
            if vals:
                out.append({name: ('in' if op == '=' else 'not in', vals)})
            continue
        v = args.get(name)
        if not filled(v):
            continue
        if f['type'] in ('select', 'boolean'):
            out.append({name: ('in' if op == '=' else 'not in', [v])})
        elif op == '=':
            out.append({name: typed(f, v)})
        elif op == 'like':
            out.append({name: ('like', f'%{v}%')})
        else:
            out.append({name: (f['sql_op'], typed(f, v))})
    return out
