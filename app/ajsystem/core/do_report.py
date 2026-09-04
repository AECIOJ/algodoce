"""Orquestrador de relatórios PDF — dict declarativo → HTML com PDF embutido.

O motor fica em `core/pdf.py` (gerar_pdf_relatorio); este módulo concentra o
glue: gera os bytes do PDF e os entrega como `Response` inline (`do_report`)
ou embutidos em data URI dentro do fragmento/página de impressão
(`print_report` / `print_report_page`).

Fluxo (sem rotas): a action do botão constrói os dados, chama
`print_report(DICT, data=...)` e o HTML retornado é injetado no container.

Formato declarativo do Report (ver `defs.report.ReportBody`):
    body:
      source:  entity (str) | {entity, ...} | Query  → de onde vêm os dados
      table:   {columns, hierarchy, footer, after, ...}  → formato tabela
      form:    {campo: pos}  → formato campo/valor (reservado)
      before / after
"""
import base64
import importlib
import os
import re
import uuid
from io import BytesIO

from flask import Response, current_app, render_template, request

from app.ajsystem.core.pdf import gerar_pdf_relatorio
from app.ajsystem.defs.data import _auto_label
from app.ajsystem.defs.report import parse_report

ERRO_MSG_PADRAO = 'Erro na impressão do Relatório'
ERRO_TEMPLATE = 'components/print_erro.html'

# Registro em memória de impressões com escolha pendente (filter_select).
# Mapeia um id curto → {report, field}, preenchido quando `print_report` monta
# o modal e consumido pelo `do_list` no retorno do submit (render interno).
_PENDING_PRINTS = {}


class FilterSelect:
    """Escolha de filtro na impressão — gerada por `filter_select(campo)`.

    Referencia um campo da Entity (ex. `tipo`); as options do modal vêm da
    propria `options` do campo na Entity. Ao submeter o modal, `value` lê o
    valor escolhido da query string e `criteria()` devolve o critério de
    igualdade `{campo: valor}` (None/vazio = sem filtro) aplicado como WHERE
    no `source` do relatório.
    """
    def __init__(self, field):
        self.field = field

    @property
    def value(self):
        return request.args.get(self.field)

    def criteria(self):
        v = self.value
        if v in (None, ''):
            return None
        return {self.field: v}


def filter_select(field):
    """Predicado genérico de impressão com escolha do usuário.

    Uso: `print_report(REPORT, filter_select('tipo'))`. Sem valor na request o
    motor devolve um modal de seleção (options do campo na Entity) e, após a
    escolha, aplica `WHERE campo = valor` no `source` e gera o PDF.
    """
    return FilterSelect(field)


def _print_erro(msg=None):
    """View padrão de erro de impressão (fragmento/página interna)."""
    return render_template(ERRO_TEMPLATE, msg=msg or ERRO_MSG_PADRAO)


def _entity_for(entity_name):
    """Resolve a `Entity` do modelo declarado em `body.source.entity`.

    List/Form enxergam a Entity via `request.blueprint`; já os reports novos
    declaram `body.source = {entity: 'Operacao', ...}`. Nesse caso a Entity vive
    no mesmo módulo do model (`app.models.<snake>.Entity`). Fallback gerenciado
    por quem chama — a fonte primária continua `_module_entity()`.
    """
    if not entity_name:
        return None
    import re as _re
    key = _re.sub(r'(?<!^)(?=[A-Z])', '_', entity_name).lower()
    try:
        mod = importlib.import_module(f'app.models.{key}')
    except ImportError:
        return None
    return getattr(mod, 'Entity', None)


def _module_entity(report=None):
    """Variável Entity do módulo corrente — como List/Form enxergam.

    Descoberta pela dupla padrão do Flask: request.blueprint →
    current_app.blueprints[...].import_name (= caminho do módulo, gravado
    por montar_blueprint). Fora de um request de blueprint, tenta a Entity
    declarada em `body.source` (via `_entity_for`).
    """
    from flask import request
    try:
        bp_name = request.blueprint
    except RuntimeError:
        bp_name = None
    if bp_name:
        bp = current_app.blueprints.get(bp_name)
        if bp is not None:
            try:
                mod = importlib.import_module(bp.import_name)
            except ImportError:
                mod = None
            if mod is not None:
                ent = getattr(mod, 'Entity', None)
                if ent:
                    return ent
    if report is not None:
        body = _body_of(report)
        src = body.get('source') if isinstance(body, dict) else (getattr(body, 'source', None) if body else None)
        entity_name = None
        if isinstance(src, str):
            entity_name = src
        elif isinstance(src, dict):
            entity_name = src.get('entity')
        if entity_name:
            return _entity_for(entity_name)
    return None


def _resolve_logo(report):
    """Resolve o path absoluto da logo a partir do path relativo do Report."""
    return os.path.join(current_app.root_path, report.logo_path)


def _body_of(report):
    if isinstance(report, dict):
        return report.get('body')
    return getattr(report, 'body', None)


def _source_of(report):
    body = _body_of(report)
    return getattr(body, 'source', None) if body else None


def _pdf_bytes(report, data=None, instance=None):
    """Gera os bytes do PDF para um report já resolvido.

    `data` omitido + instance presente → extrai `instance.<data_attr>`
    (o atributo de dados vem do source dict quando informado).
    """
    if data is None and instance is not None:
        src = _source_of(report)
        data_attr = 'items'
        if isinstance(src, dict):
            data_attr = src.get('data_attr', 'items')
        data = getattr(instance, data_attr, None)
    logo = _resolve_logo(report)
    pdf = gerar_pdf_relatorio(report, data, logo, instance=instance)
    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()


def _data_uri(raw):
    return f'data:application/pdf;base64,{base64.b64encode(raw).decode("ascii")}'


def _calc_fn(expr):
    """Converte expressão `calc` da Entity em function(row) para o PDF."""
    def fn(row):
        ns = {t: (getattr(row, t, 0) or 0)
              for t in re.findall(r'[A-Za-z_][A-Za-z0-9_]*', expr)}
        return eval(expr, {'__builtins__': {}}, ns)
    return fn


def _apply_entity(raw, entity):
    """Resolve os campos do Report (`header.fields`, `body.table.columns`,
    `body.table.hierarchy`, `body.source`) contra a `Entity` do módulo.

    `entity` = variável Entity do módulo corrente (via blueprint). Para cada
    referência, herda `label` + apresentação inferida do type (`NUM`→brl right,
    `DATA`→datetime right, `INT`→center) e o `calc`/`function` da Entity.

    Sem entity (fora de blueprint) nada é resolvido. Retorna cópia ajustada;
    não muta o declarado.
    """
    if not entity:
        return raw
    out = dict(raw)

    def _locate(field):
        # Entity flat: {'campo': cfg} — o nome do campo é a própria chave.
        if field in entity and isinstance(entity.get(field), dict):
            return field
        # Entity legada aninhada: {'Model': {'campo': cfg}}.
        hits = [m for m, cfg in entity.items()
                if isinstance(cfg, dict) and field in cfg]
        return hits[0] if len(hits) == 1 else None

    def _infer_presentation(cfg):
        from app.ajsystem.core.utils import normalize_currency
        t, inp, cur = cfg.get('type'), cfg.get('input'), cfg.get('currency')
        fmt = align = None
        if cur:
            fmt, align = normalize_currency(cur), 'right'
        elif t == 'NUM':
            fmt, align = 'brl', 'right'
        elif t == 'DATA' or inp == 'date':
            fmt, align = 'datetime', 'right'
        elif t == 'INT':
            align = 'center'
        return {'format': fmt, 'align': align}

    def _resolve_map(items):
        if isinstance(items, list):
            # forma enxuta: strs puros + dicts (calculados/overrides)
            norm = {}
            for i, it in enumerate(items):
                if isinstance(it, str):
                    norm[it] = {}
                    continue
                it = dict(it)
                k = it.pop('name', None) or it.get('field') or f'_{i}'
                norm[k] = it
            items = norm
        if not isinstance(items, dict):
            return None
        resolved = {}
        for key, extra in items.items():
            extra = dict(extra or {})
            if '.' in key:
                model, fld = key.split('.', 1)
            else:
                model = _locate(key)
                fld = key
            if model and model in entity:
                # Entity flat ({campo: cfg}): model == fld → a própria entrada é a config.
                raw_cfg = entity[model] if model == fld else entity[model].get(fld, {})
                base = {'label': raw_cfg.get('label') or _auto_label(fld),
                        **_infer_presentation(raw_cfg)}
                spec = {**{k: v for k, v in base.items() if v is not None},
                        **extra}
                # FK → caminho de exibição via relacionamento ('<base>.nome')
                if (raw_cfg.get('type') == 'FK' and 'field' not in spec
                        and key.endswith('_id')):
                    spec['field'] = f'{key[:-3]}.nome'
                # calc da Entity → function(row) quando não informada
                if raw_cfg.get('calc') and 'function' not in spec:
                    calc = raw_cfg['calc']
                    spec['function'] = calc if callable(calc) else _calc_fn(calc)
                # BOOL → Sim/Não · LIST → label das options
                if raw_cfg.get('type') == 'BOOL' and 'function' not in spec:
                    spec['function'] = lambda row, f=fld: (
                        'Sim' if getattr(row, f, None) else 'Não')
                if raw_cfg.get('type') == 'LIST' and 'function' not in spec:
                    opts = raw_cfg.get('list') or raw_cfg.get('options') or {}
                    spec['function'] = lambda row, f=fld, o=opts: (
                        o.get(getattr(row, f, None), getattr(row, f, '')))
                resolved[key] = spec
                continue
            # não resolvido na Entity: exige identidade p/ descartar typo
            if not any(k in extra for k in ('label', 'function')):
                raise KeyError(
                    f"Campo '{key}' não resolvido na Entity (ausente ou "
                    f"ambíguo — use 'Model.campo') e sem 'label'/'function' "
                    f"(report '{raw.get('label')}')"
                )
            resolved[key] = extra
        return resolved

    # header.fields
    header = out.get('header')
    if isinstance(header, dict):
        specs = _resolve_map(header.get('fields'))
        if specs is not None:
            out['header'] = {**header, 'fields': [
                {'field': k, **v} for k, v in specs.items()]}

    # body.table.columns + body.table.hierarchy
    body = out.get('body')
    if isinstance(body, dict):
        body = dict(body)
        table = body.get('table')
        if isinstance(table, dict):
            table = dict(table)
            specs = _resolve_map(table.get('columns'))
            if specs is not None:
                cols = {}
                for key, spec in specs.items():
                    spec = dict(spec)
                    data_key = spec.pop('field', None) or key
                    cols[data_key] = spec
                table['columns'] = cols

            hier = table.get('hierarchy')
            if hier:
                items = (hier.items() if isinstance(hier, dict)
                         else [(k, v) for h in hier for k, v in (h or {}).items()])
                specs = []
                for field, o in items:
                    o = dict(o or {})
                    sp = {'field': field,
                          'pos': o.pop('pos', 1),
                          'total': o.pop('total', True),
                          'line': o.pop('line', True),
                          'eject': o.pop('eject', False)}
                    if 'left' in o:
                        sp['left'] = max(1, int(o.pop('left')))
                    sp.update(o)
                    model = _locate(field)
                    if model:
                        # Entity flat ({campo: cfg}): model == field → a própria entrada.
                        raw_cfg = entity[model] if model == field else entity[model].get(field, {})
                        sp['label'] = raw_cfg.get('label') or _auto_label(field)
                        opts = raw_cfg.get('list') or raw_cfg.get('options')
                        if opts:
                            sp['options'] = opts
                        if raw_cfg.get('calc') and 'function' not in sp:
                            calc = raw_cfg['calc']
                            sp['function'] = calc if callable(calc) else _calc_fn(calc)
                        if raw_cfg.get('type') == 'FK':
                            sp['fk_path'] = f'{field[:-3] if field.endswith("_id") else field}.nome'
                    else:
                        sp['label'] = o.pop('label', _auto_label(field))
                    sp.update(o)
                    ttxt = sp.get('text')
                    if ttxt:
                        fo = {}
                        for nm in set(re.findall(r'{(\w+)}', ttxt)):
                            mdl = _locate(nm)
                            if mdl:
                                o_ = entity[mdl] if mdl == nm else entity[mdl].get(nm, {})
                                lst = o_.get('list') or o_.get('options')
                                if lst:
                                    fo[nm] = lst
                        if fo:
                            sp['_fmt_opts'] = fo
                    specs.append(sp)
                table['hierarchy'] = specs
            body['table'] = table

        source = body.get('source')
        if isinstance(source, str):
            src_model = _locate(source)
            if src_model is None and source in entity:
                src_model = source
        out['body'] = body

    return out


def _infer_source(report, entity):
    """Model de origem dos dados da tabela, deduzido de `body.source`.

    `body.source` pode ser:
      - string (entity name)          → entity implícita, sem ordenação declarada
      - dict {entity, order, ...}     → ordenação declarada em `order`
      - Query                         → (reservado; trata como entity se possível)

    A ordenação é **exclusivamente** declarada por `source.order`; a hierarchy
    não participa da ordenação (é apenas leitura/change-detection).
    `order` pode ser:
      - campo calculado na Entity (`calc` callable) → ordenação python-side;
      - coluna real do banco                        → `order_by` SQL.

    Retorna dict com model_name, data_attr, order_mode ('sql'|'calc'|None),
    sort_fn (calc) e order_field (coluna).
    """
    from app.ajsystem.core.list import _resolve_model
    body = _body_of(report)
    src = body.get('source') if isinstance(body, dict) else (getattr(body, 'source', None) if body else None)
    if src is None:
        return {'name': None, 'data_attr': 'items', 'order_mode': None,
                'sort_fn': None, 'order_field': None}
    entity_name = src if isinstance(src, str) else (
        src.get('entity') if isinstance(src, dict) else None)
    data_attr = src.get('data_attr', 'items') if isinstance(src, dict) else None
    order = src.get('order') if isinstance(src, dict) else None
    if not entity_name:
        return {'name': None, 'data_attr': data_attr, 'order_mode': None,
                'sort_fn': None, 'order_field': None}

    info = {'name': entity_name, 'data_attr': data_attr,
            'order_mode': None, 'sort_fn': None, 'order_field': order}
    if not order or not entity:
        return info

    model = _resolve_model(entity_name)
    if model is None:
        return info
    if hasattr(model, order):
        info['order_mode'] = 'sql'
        info['order_field'] = getattr(model, order)
        return info

    raw_cfg = (entity.get(order, {}) if order in entity else None)
    if isinstance(raw_cfg, dict):
        calc = raw_cfg.get('calc')
        if callable(calc):
            info['order_mode'] = 'calc'
            info['sort_fn'] = calc
    return info


def _auto_data(report, data, instance, filter=None):
    """Precedência do datasource: `data` explícito → `instance.<data_attr>` →
    `body.source` (entity). Ordenação declarada por `source.order`: coluna →
    `order_by` SQL; calc → `sorted` python-side.

    `filter` aplica o critério `body.filter` à query antes da ordenação:
      - dict `{campo: valor}` → igualdade (`model.campo == valor`);
      - callable `f(model, value=...)` → retorna o critério.
    Se `filter` (arg) vier preenchido, sobrescreve o valor default do dict.
    """
    filtro = getattr(_body_of(report), 'filter', None) if _body_of(report) else None
    if isinstance(filter, dict):
        # valores vindos da request (ex. {'tipo': 1}) fundem/sobrescrevem o default
        filtro = {**(filtro or {}), **filter}
    elif filter is not None:
        filtro = filter

    if data is not None or instance is not None:
        if data is None and instance is not None:
            info = _infer_source(report, _module_entity(report))
            data = getattr(instance, info['data_attr'] or 'items', None)
        return data

    info = _infer_source(report, _module_entity(report))
    name = info['name']
    if not name:
        return None
    from app.ajsystem.core.list import _resolve_model
    model = _resolve_model(name)
    query = model.query
    if filtro:
        query = _apply_report_filter(query, model, filtro)
    if info['order_mode'] == 'sql':
        out = list(query.order_by(info['order_field']).all())
    else:
        out = list(query.all())
    if info['order_mode'] == 'calc' and out:
        out = sorted(out, key=info['sort_fn'])
    return out


def _apply_report_filter(query, model, filtro):
    """Aplica o critério `body.filter` à query.

    dict `{campo: valor}` → igualdade (valor None = sem critério no campo);
    callable `f(model, query, value=...)` → retorna a query filtrada.
    """
    if callable(filtro):
        crit = filtro(model)
        return crit if crit is not None else query
    for campo, valor in (filtro or {}).items():
        if valor is None:
            continue
        col = getattr(model, campo, None)
        if col is not None:
            query = query.filter(col == valor)
    return query


def print_report_page(report, instance=None, data=None, msg=None, filter=None):
    """Retorna página completa com iframe do PDF embutido (data URI)."""
    report = parse_report(_apply_entity(report, _module_entity(report)))
    data = _auto_data(report, data, instance, filter)
    try:
        src = _data_uri(_pdf_bytes(report, data, instance))
        return render_template(report.print_template, pdf_url=src)
    except Exception:
        return _print_erro(msg)


def print_report(report, instance=None, data=None, msg=None, filter=None,
                 _printing=False):
    """Retorna fragmento HTML com iframe do PDF embutido (data URI).

    Contrato para uso em botões (`action`): recebe o dict do relatório,
    os dados já construídos pelo app e retorna o fragmento; string vazia
    não injeta nada. `filter` (dict {campo: valor} ou callable) aplica o
    critério `body.filter` à query antes da ordem. Falha → view padrão
    `print_erro.html` com `msg`.

    `filter` também aceita o predicado `filter_select(campo)`: sem valor na
    request devolve um modal de escolha (render interno) e, após a escolha
    (`_printing=True`), aplica `WHERE campo = valor` no `source` e gera o PDF.
    O predicado pode ser passado no 2º posicional (`print_report(PLANO, fs)`)
    ou via `filter=fs` — os dois são normalizados para o argumento filter.
    """
    if isinstance(instance, FilterSelect):
        if filter is not None:
            raise TypeError('filter_select recebido junto de `filter`')
        filter, instance = instance, None
    if isinstance(filter, FilterSelect):
        if not _printing:
            return _print_with_choice(report, filter, msg)
        report = parse_report(_apply_entity(report, _module_entity(report)))
        data = _auto_data(report, data, instance, filter.criteria())
        try:
            src = _data_uri(_pdf_bytes(report, data, instance))
            return render_template(report.print_fragment_template, pdf_url=src)
        except Exception:
            return _print_erro(msg)
    report = parse_report(_apply_entity(report, _module_entity(report)))
    data = _auto_data(report, data, instance, filter)
    try:
        src = _data_uri(_pdf_bytes(report, data, instance))
        return render_template(report.print_fragment_template, pdf_url=src)
    except Exception:
        return _print_erro(msg)


def _print_with_choice(report, fs, msg=None):
    """Monta o modal de escolha para `FilterSelect` e registra a impressão.

    Devolve sempre o modal (nunca o PDF) — assim o template do botão fica
    limpo e o usuário pode reimprimir com outro critério. O PDF de retorno é
    gerado pelo `do_list` via `_consume_pending_print` (render interno).
    """
    entity_name = _infer_source(report, _module_entity(report)).get('name')
    entity = _entity_for(entity_name) or _module_entity(report)
    options = {}
    label = _auto_label(fs.field)
    if entity and fs.field in entity:
        cfg = entity[fs.field] if isinstance(entity[fs.field], dict) else {}
        options = cfg.get('options') or cfg.get('list') or {}
        label = cfg.get('label') or label
    rid = uuid.uuid4().hex[:12]
    _PENDING_PRINTS[rid] = {'report': report, 'field': fs.field}
    title = report.get('label') if isinstance(report, dict) else 'Imprimir'
    return choice_modal(
        title=title,
        label=label,
        options=options,
        param=fs.field,
        confirm_label='Imprimir',
        hidden_params={'_r': rid},
    )


def _consume_pending_print(rid):
    """Gera o fragmento PDF de uma impressão pendente (chamado pelo `do_list`).

    Consome o registro criado pelo modal de `filter_select`, aplicando o valor
    escolhido na request como WHERE no `source`. `None` se o id não existe
    (impressão expirada/não registrada).
    """
    pend = _PENDING_PRINTS.pop(rid, None)
    if not pend:
        return None
    try:
        return print_report(pend['report'], FilterSelect(pend['field']),
                            _printing=True)
    except Exception:
        return None


def _print_field_of(rid):
    """Campo da impressão pendente correspondente ao marcador `_r` (sem consumir).

    Usado pelo `do_list` para não aplicar como filtro da listagem o parâmetro
    que o relatório injetou na URL — assim o filtro de impressão não persiste
    na listagem ao voltar. `None` se não há impressão pendente para o id.
    """
    pend = _PENDING_PRINTS.get(rid)
    return pend['field'] if pend else None


def do_report(report, data=None, instance=None, filename="relatorio.pdf",
              as_response=True):
    """Gera e devolve o relatório configurado por `report` (dict ou Report).

    `as_response=True` → `flask.Response` (inline PDF) para a rota retornar.
    `as_response=False` → objeto FPDF (para testes/uso programático).
    """
    report = parse_report(report)
    if not as_response:
        from app.ajsystem.core.pdf import gerar_pdf_relatorio as _g
        return _g(report, data, _resolve_logo(report), instance=instance)
    raw = _pdf_bytes(report, data, instance)
    return Response(
        raw,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"},
    )


def choice_modal(title, options, param='tipo', label='Escolha',
                 confirm_label='Ok', hidden_params=None, url_target=None):
    """Modal genérico de escolha (fragmento injetado via reportRender).

    Devoluível por qualquer action de botão: aberto ao injetar; um `<select>`
    com `options` ({valor: rótulo}) + opção implícita 'Todos' (vazio). Ao
    escolher, o form faz GET para `url_target` (padrão: a URL atual) com
    `?<param>=<valor>` + `hidden_params`.

    Como o submit re-renderiza a própria página, a função da Page deve, no
    render seguinte, detectar `request.args.get('param')` e gerar o relatório.
    Default de `url_target` é `request.path` (sem query) — os parâmetros vêm do
    próprio form (select + hiddens), evitando arrastar query antiga da URL.
    """
    url = url_target or request.path
    return render_template(
        'components/choice_modal.html',
        uid=uuid.uuid4().hex[:8],
        title=title,
        label=label,
        options=options,
        param=param,
        confirm_label=confirm_label,
        url_target=url,
        hidden_params=(hidden_params or {}),
    )
