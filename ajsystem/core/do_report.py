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

from ajsystem import locales as i18n
from ajsystem.core.pdf import gerar_pdf_relatorio
from ajsystem.core.resolve import (
    field_display_fn,
    field_presentation,
    field_spec_item,
    field_spec_items,
    select_entry_computed as _computed_e,
    select_entry_props as _props_e,
)
from ajsystem.defs.data import _auto_label
from ajsystem.defs.report import parse_report

ERRO_TEMPLATE = 'components/print_erro.html'
# Fragmento injetado pelo print_report: overlay do framework (fragmento com
# o iframe + alternância do container; redundante sob reportRender, vital no
# standalone — o script só age se o container existir).
OVERLAY_TEMPLATE = 'components/print_overlay.html'

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
    return render_template(ERRO_TEMPLATE, msg=msg or i18n.REPORT_ERROR)


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
    """Entity merged (Schema ∪ Entity do model) do módulo corrente.

    Descoberta pela dupla padrão do Flask: request.blueprint →
    current_app.blueprints[...].import_name (= caminho do módulo, gravado
    por montar_blueprint). Como List/Form, cada entidade do `Schema` da rota
    é resolvida via `resolve_entity_fields` (Entity do model ∪ Schema), e o
    resultado é exposto no formato aninhado `{NomeEntidade: campos_merged}`
    que o `_apply_entity` consume.

    Fallbacks, em ordem: `Entity` declarada no próprio módulo (rotas legadas
    e de site) e a Entity do model declarada em `body.source` (via
    `_entity_for`).
    """
    from ajsystem.core.list import _resolve_model
    from ajsystem.defs.data import resolve_entity_fields
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
                schema = getattr(mod, 'Schema', None) or {}
                if schema:
                    merged = {}
                    for ent in schema:
                        try:
                            model = _resolve_model(ent)
                        except Exception:
                            continue
                        merged[ent] = resolve_entity_fields(schema, model, ent)
                    if merged:
                        return merged
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
            entity_name = src.get('entity', src.get('from'))
            if isinstance(entity_name, (list, tuple)):
                entity_name = entity_name[0] if entity_name else None
        if entity_name:
            return _entity_for(entity_name)
    return None


def _resolve_logo(report):
    """Logo do APP (`APP.logo`, relativo ao static) com fallback legado."""
    from ajsystem.defs.report import LOGO_FALLBACK
    try:
        from ajsystem.core.adapter import APP
        _logo = getattr(APP, 'logo', None)
    except Exception:
        _logo = None
    if _logo:
        return os.path.join(current_app.static_folder, _logo)
    return os.path.join(current_app.root_path, LOGO_FALLBACK)


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

    # Entidade principal (campos sem prefixo) do report.
    from ajsystem.core.list import _resolve_model as _rmodel
    _pname = _principal_name(out, entity)
    try:
        _pmodel = _rmodel(_pname) if _pname else None
    except Exception:
        _pmodel = None

    # Defaults vindos das entradas do select (props de apresentação da query),
    # via `core.resolve` — as mesmas primitivas que a listagem usa em
    # `query_select_layer`. Precedência: Entity/Schema -> entrada (query) ->
    # inline do relatório.
    _disp_map = {}
    _computed = set()
    try:
        from ajsystem.defs.qspec import parse_select as _ps
        _src = (out.get('body') or {}).get('source') if isinstance(out.get('body'), dict) else None
        if isinstance(_src, dict) and 'select' in _src and 'from' in _src:
            for _e in _ps(_src.get('select')):
                # o report tem a prop `format` (a listagem não), por isso as
                # 4 chaves em vez do `SELECT_PROPS` da máquina.
                _d = _props_e(_e, ('label', 'width', 'align', 'format'))
                if _d:
                    _disp_map[_e.name] = _d
                if _computed_e(_e):
                    _computed.add(_e.name)
            _hier = (_src.get('levels', _src.get('hierarchy')) or {})
            _blevels = ((out.get('body') or {}).get('levels') or {})
            if isinstance(_blevels, dict) and _blevels.get('target'):
                _hier = _blevels
            if isinstance(_hier, dict) and _hier.get('target'):
                _computed.add(_hier['target'])
    except Exception:
        _disp_map = {}
        _computed = set()

    def _infer_presentation(cfg):
        # A decisão é genérica (máscara → moeda; type/input → formato):
        # `core.resolve.field_presentation`, compartilhada com a busca.
        fmt, align = field_presentation(cfg)
        return {'format': fmt, 'align': align}

    def _resolve_map(items):
        # Lista solta de itens → `{nome: overrides}`: a gramática é a
        # genérica (`core.resolve.field_spec_items`, as formas de
        # `list.columns`). Item que não nomeia um field cai em `_0`, `_1`…,
        # a forma legada em que um dict de props ainda é um campo.
        if isinstance(items, list):
            items = field_spec_items(items)
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
                # overrides de field exclusivamente via Schema/Entity: base (Entity+Schema) tem precedência
                # sobre inline do report para label/format/align (report mantém apenas width/agg/report-specific)
                raw_cfg = entity[model] if model == fld else entity[model].get(fld, {})
                base = {'label': raw_cfg.get('label') or _auto_label(fld),
                        **_infer_presentation(raw_cfg)}
                # base (Schema) vence para label/format/align; extra (report) mantém width/agg etc.
                _base_filtered = {k: v for k, v in base.items() if v is not None}
                # Query (entrada do select) sobre Entity/Schema; report inline por cima.
                _qp = _disp_map.get(fld) or _disp_map.get(key) or {}
                spec = {**_base_filtered, **_qp, **extra}
                # Máscara manda (genérico, igual à list): format declarado no
                # relatório vence; máscara (Entity/Schema/query/catálogo) vence
                # a inferência por type. BOOL/LIST com rótulo não mascaram.
                _mapped_label = False
                _explicit_fmt = extra.get('format') or _qp.get('format')
                # FK → caminho de exibição via relacionamento ('<base>.nome')
                if (raw_cfg.get('type') == 'FK' and 'field' not in spec
                        and key.endswith('_id')):
                    spec['field'] = f'{key[:-3]}.nome'
                # calc da Entity → function(row) - exclusivamente via Schema/Entity
                # (report não deve redefinir function quando Entity já tem calc).
                # Exceção: coluna já computada pela query (over/hierarchy) -> attr
                # direto (1 query, sem N+1 por célula).
                if fld in _computed:
                    spec.pop('function', None)
                elif raw_cfg.get('calc'):
                    calc = raw_cfg['calc']
                    if isinstance(calc, (str,)) or callable(calc):
                        spec['function'] = calc if callable(calc) else _calc_fn(calc)
                else:
                    # BOOL → Sim/Não · LIST → rótulo do catálogo: passo genérico
                    # (`core.resolve.field_display_fn`), o mesmo que
                    # `_field_item` usa — é por isso que coluna e item de
                    # layout imprimem igual. Fora daqui (calc acima) a Entity
                    # manda, porque quem calcula o valor é o `calc`.
                    _disp_fn = field_display_fn(raw_cfg, fld, i18n)
                    if _disp_fn is not None:
                        spec['function'] = _disp_fn
                        _mapped_label = True
                if fld not in _computed and _explicit_fmt is None and not _mapped_label:
                    _fcfg = {**raw_cfg,
                             **{k: v for k, v in _qp.items() if k != 'format'}}
                    if extra.get('mask'):
                        _fcfg = {**_fcfg, 'mask': extra['mask']}
                    _mask = _field_mask(fld, _fcfg)
                    if _mask:
                        spec.pop('format', None)
                        spec['format'] = _mask
                resolved[key] = spec
                continue
            # não resolvido na Entity: display do select (nascidos) como default;
            # text monta a célula via template (ex. código) — senão exige
            # identidade p/ descartar typo
            if key in _disp_map:
                spec = {**_disp_map[key], **extra}
                if 'label' not in spec:
                    spec['label'] = _auto_label(key)
                resolved[key] = spec
                continue
            if 'text' in extra:
                spec = dict(extra)
                spec.setdefault('label', _auto_label(key))
                spec['function'] = _cell_text_fn(extra['text'], entity)
                resolved[key] = spec
                continue
            if not any(k in extra for k in ('label', 'function')):
                raise KeyError(
                    f"Campo '{key}' não resolvido na Entity (ausente ou "
                    f"ambíguo — use 'Model.campo') e sem 'label'/'function' "
                    f"(report '{raw.get('label')}')"
                )
            resolved[key] = extra
        return resolved

    # header.fields (dict) ou header=[...] (lista: FIELDs resolvidos na Entity)
    header = out.get('header')
    if isinstance(header, dict):
        specs = _resolve_map(header.get('fields'))
        if specs is not None:
            out['header'] = {**header, 'fields': [
                {'field': k, **v} for k, v in specs.items()]}
    elif isinstance(header, list):
        from ajsystem.defs.report import parse_report_item as _pri
        header = _expand_fields_list(header, entity, raw.get('label'), _pname, _pmodel)
        _flist, _fpos = [], []
        for _i, _it in enumerate(header):
            try:
                _ri = _pri(_it, raw.get('label'))
            except ValueError:
                continue
            if _ri.kind == 'FIELD':
                _flist.append(_it if isinstance(_it, str) else {'field': _ri.name, **_ri.config})
                _fpos.append(_i)
        if _flist:
            _fspecs = _resolve_map(_flist) or {}
            _header = list(header)
            for _i, _it in zip(_fpos, _flist):
                _key = _it if isinstance(_it, str) else (_it.get('field') or next(iter(_it)))
                _sp = dict(_fspecs.get(_key, {}))
                _header[_i] = ({'field': _sp.pop('field', _key), **_sp}
                               if isinstance(_it, dict) else {'field': _key, **_sp})
            out['header'] = _header
        _attach_text_opts(out.get('header') if isinstance(out.get('header'), list) else None,
                          entity, raw.get('label'))

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
                    for _fk in ('font', 'cpp', 'font_size'):
                        if _fk in spec:
                            raise ValueError(f"report '{raw.get('label')}': '{_fk}' não vale em tabela (sempre cpp=0)")
                    data_key = spec.pop('field', None) or key
                    cols[data_key] = spec
                table['columns'] = cols

            _ext = []
            for _ex in table.get('extend') or []:
                if isinstance(_ex, tuple) and len(_ex) >= 2 and isinstance(_ex[1], str):
                    _fo = _fmt_opts_for(_ex[1], entity)
                    if _fo:
                        _ex = list(_ex)
                        _pp = dict(_ex[2]) if len(_ex) == 3 else {}
                        _pp.setdefault('_fmt_opts', _fo)
                        _ex = tuple([_ex[0], _ex[1], _pp] if len(_ex) == 3 else [_ex[0], _ex[1]])
                _ext.append(_ex)
            if _ext:
                table['extend'] = _ext
            _synthesize_levels_from_groups(table, out.get('body') or {}, raw.get('label'))
            hier = table.get('levels', table.get('hierarchy'))
            if hier:
                items = (hier.items() if isinstance(hier, dict)
                         else [(k, v) for h in hier for k, v in (h or {}).items()])
                specs = []
                for field, o in items:
                    o = dict(o or {})
                    sp = {'field': field,
                          'pos': o.pop('pos', 1),
                          'total': o.pop('total', True),
                          'gline': o.pop('gline', o.pop('line', True)),
                          'eject': o.pop('eject', False)}
                    if 'left' in o:
                        sp['left'] = max(1, int(o.pop('left')))
                    sp.update(o)
                    model = _locate(field)
                    if model:
                        # Entity flat ({campo: cfg}): model == field → a própria entrada.
                        # overrides exclusivamente via Schema/Entity: label/options/calc da Entity vencem
                        raw_cfg = entity[model] if model == field else entity[model].get(field, {})
                        sp['label'] = raw_cfg.get('label') or _auto_label(field)
                        opts = raw_cfg.get('list') or raw_cfg.get('options')
                        if opts:
                            sp['options'] = opts
                        if raw_cfg.get('calc'):
                            calc = raw_cfg['calc']
                            if isinstance(calc, (str,)) or callable(calc):
                                sp['function'] = calc if callable(calc) else _calc_fn(calc)
                        if raw_cfg.get('type') == 'FK':
                            sp['fk_path'] = f'{field[:-3] if field.endswith("_id") else field}.nome'
                        # report não sobrescreve label/options/function da Entity
                        for _k in ('label', 'options', 'function', 'fk_path'):
                            if _k in o and _k in sp and sp[_k] != o[_k]:
                                # mantém Entity, descarta override do report
                                pass
                    else:
                        sp['label'] = o.pop('label', _auto_label(field))
                    # não re-aplica o dict do report por cima da Entity para label/function
                    for _k, _v in o.items():
                        if _k not in ('label', 'options', 'function', 'fk_path'):
                            sp[_k] = _v
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
                table['levels'] = specs
                table.pop('hierarchy', None)
            body['table'] = table

        source = body.get('source')
        if isinstance(source, str):
            src_model = _locate(source)
            if src_model is None and source in entity:
                src_model = source
        if isinstance(body.get('items'), list):
            body['items'] = _expand_fields_list(body['items'], entity, raw.get('label'), _pname, _pmodel)
            body['items'] = _attach_field_mask(body['items'], entity, raw.get('label'))
        _attach_text_opts(body.get('items'), entity, raw.get('label'))
        _after = body.get('after')
        if isinstance(_after, list):
            body['after'] = _expand_fields_list(_after, entity, raw.get('label'), _pname, _pmodel)
            body['after'] = _attach_field_mask(body['after'], entity, raw.get('label'))
            _attach_text_opts(body['after'], entity, raw.get('label'))
        _tbl = body.get('table') or {}
        _tbl_after = _tbl.get('after')
        if isinstance(_tbl_after, list):
            _tbl['after'] = _expand_fields_list(_tbl_after, entity, raw.get('label'), _pname, _pmodel)
            _tbl['after'] = _attach_field_mask(_tbl['after'], entity, raw.get('label'))
            _attach_text_opts(_tbl['after'], entity, raw.get('label'))
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
    from ajsystem.core.list import _resolve_model
    body = _body_of(report)
    src = body.get('source') if isinstance(body, dict) else (getattr(body, 'source', None) if body else None)
    if src is None:
        return {'name': None, 'data_attr': 'items', 'order_mode': None,
                'sort_fn': None, 'order_field': None}
    entity_name = src if isinstance(src, str) else None
    if entity_name is None and isinstance(src, dict):
        # Legado usa 'entity'; query nova usa 'from' (str ou [entidade, ...]).
        entity_name = src.get('entity', src.get('from'))
        if isinstance(entity_name, (list, tuple)):
            entity_name = entity_name[0] if entity_name else None
    data_attr = src.get('data_attr', 'items') if isinstance(src, dict) else None
    order = src.get('order') if isinstance(src, dict) else None
    if not entity_name:
        return {'name': None, 'data_attr': data_attr, 'order_mode': None,
                'sort_fn': None, 'order_field': None}

    info = {'name': entity_name, 'data_attr': data_attr,
            'order_mode': None, 'sort_fn': None, 'order_field': order}
    if not order or not entity:
        return info
    if isinstance(order, (list, tuple)):
        return info  # query nova: ordem composta resolvida no qrun

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


def _fmt_opts_for(tpl, entity):
    """Mapa {campo: options} p/ templates (LIST da Entity; pontilhado: base)."""
    import re as _re
    out = {}
    for nm in set(_re.findall(r'{([\w.]+)(?::[^}]*)?}', tpl or '')):
        base = nm.split('.')[0]
        mdl = None
        if entity and base in entity and isinstance(entity.get(base), dict):
            mdl = base
        else:
            hits = [m for m, cfg in (entity or {}).items()
                    if isinstance(cfg, dict) and base in cfg] if entity else []
            mdl = hits[0] if len(hits) == 1 else None
        if mdl:
            raw_cfg = entity[mdl] if mdl == base else entity[mdl].get(base, {})
            opts = raw_cfg.get('list') or raw_cfg.get('options')
            if opts:
                out[nm] = opts
    return out


def _related_cfg(name, entity):
    """Cfg {campo: cfg} do model relacionado (Schema da rota vence Entity)."""
    if isinstance(entity, dict) and name in entity and isinstance(entity[name], dict):
        return entity[name]
    return _entity_for(name) or {}


def _relation_to(source_model, target_entity):
    """Nome da relação em `source_model` cujo alvo é `target_entity` (único).

    Usado p/ ler `<Entidade>.<campo>`: a Entity diz o alvo, a relação (FK) diz o
    caminho do atributo. Múltiplas relações → None (use o FK explícito)."""
    if source_model is None:
        return None
    try:
        rels = source_model.__mapper__.relationships
    except Exception:
        return None
    hits = [k for k, rel in rels.items()
            if rel.mapper.class_.__name__ == target_entity]
    return hits[0] if len(hits) == 1 else None


def _principal_name(out, entity):
    """Entidade principal do report (campos sem prefixo)."""
    body = out.get('body') if isinstance(out.get('body'), dict) else {}
    src = body.get('source')
    if isinstance(src, str):
        return src
    if isinstance(src, dict):
        nm = src.get('entity') or src.get('from')
        if isinstance(nm, (list, tuple)):
            nm = nm[0] if nm else None
        if nm:
            return nm
    if isinstance(entity, dict):
        for k, v in entity.items():
            if isinstance(v, dict) and k[:1].isupper():
                return k
    return None


def _field_base_cfg(entity, principal_name, name):
    """Cfg do campo na Entity (principal/aninhada/flat, senão hit único)."""
    if principal_name and isinstance(entity.get(principal_name), dict):
        c = entity[principal_name].get(name)
        if isinstance(c, dict):
            return c
    # Entity flat: {campo: cfg}
    c = entity.get(name)
    if isinstance(c, dict) and any(k in c for k in ('type', 'input', 'label', 'calc')):
        return c
    hits = [cfg[name] for cfg in entity.values()
            if isinstance(cfg, dict) and name in cfg]
    return hits[0] if len(hits) == 1 else {}


def _field_item(name, cfg, entity, principal_name, principal_model):
    """Resolve 1 item de campo do report (mesma base de columns/fields).

    `name` = 'campo' | 'Entidade.campo'. Retorna dict do item com `field`
    (caminho de leitura) + `label`/`format`/`mask` da Entity + overlay `cfg`.
    FK usa o `lookup` do Field (senão '<relação>.nome'). `function`/BOOL/LIST
    ficam pro `_resolve_map`.
    """
    from ajsystem.defs.data import (
        _FIELD_KEYS, build_field, resolve_lookup, fk_relation_name,
    )
    from ajsystem.core.list import _resolve_model
    cfg = dict(cfg or {})
    if '.' in name:
        ent_key, short = name.split('.', 1)
        base = (_related_cfg(ent_key, entity) or {}).get(short, {}) or {}
        src_model = _resolve_model(ent_key)
        rel = _relation_to(principal_model, ent_key)
        data_path = f'{rel}.{short}' if rel else name
    else:
        short = name
        base = _field_base_cfg(entity, principal_name, short)
        src_model = principal_model
        data_path = short
    fprops = {k: v for k, v in cfg.items() if k in _FIELD_KEYS}
    merged = {**base, **fprops}
    try:
        f = build_field(short, merged)
    except Exception:
        f = None
    if merged.get('type') == 'FK':
        try:
            lk = resolve_lookup(f, src_model) if f is not None else None
        except Exception:
            lk = None
        if lk:
            data_path = lk['path']
        elif short.endswith('_id'):
            rel = fk_relation_name(src_model, short) if src_model else short[:-3]
            data_path = f'{rel}.nome'
    item = {'field': data_path}
    item['label'] = f.label if f is not None else (
        base.get('label') or _auto_label(short))
    # `LIST` → rótulo do catálogo · `BOOL` → Sim/Não. O passo é o mesmo das
    # colunas (`core.resolve.field_display_fn`); sem ele, um `FIELDS('forminhas')`
    # em `after`/`items` imprimia o código enquanto a coluna imprimia o rótulo.
    _disp_fn = field_display_fn(merged, short, i18n)
    if _disp_fn is not None and 'function' not in cfg:
        item['function'] = _disp_fn
    _m = _field_mask(short, merged)
    if _m:
        item['format'] = _m
    item.update(cfg)
    return item


def _expand_fields_list(items, entity, label, principal_name=None, principal_model=None):
    """Expande FIELDS(...) em itens FIELD resolvidos.

    Cada item ('campo' ou ('campo', {props})) resolve como columns/fields;
    'Entidade' (PascalCase resolvível) expande a entidade. Sem label automático:
    o label vem da Entity (Entity/Schema) e só o override o troca.
    """
    if not isinstance(items, list):
        return items
    from ajsystem.defs.report import parse_report_item as _pri
    out = []
    for it in items:
        try:
            _ri = _pri(it, label)
        except ValueError:
            out.append(it)
            continue
        if _ri.kind != 'FIELDS':
            out.append(it)
            continue
        for spec in _ri.config.get('items') or []:
            achado = field_spec_item(spec)
            if achado is None:
                continue
            name, cfg = achado
            if name[:1].isupper():
                ent_cfg = _related_cfg(name, entity)
                if ent_cfg:
                    for fld, _fcfg in ent_cfg.items():
                        if fld.startswith('_'):
                            continue
                        full = fld if name == principal_name else f'{name}.{fld}'
                        out.append(_field_item(full, cfg, entity,
                                               principal_name, principal_model))
                    continue
            out.append(_field_item(name, cfg, entity, principal_name, principal_model))
    return out


def _raw_cfg_of(field, entity):
    """Cfg bruta do campo na Entity (flat ou aninhada), {} se ausente."""
    if not isinstance(entity, dict):
        return {}
    if isinstance(field, str) and '.' in field:
        model, fld = field.split('.', 1)
        return _raw_cfg_of(fld, _related_cfg(model, entity))
    if field in entity and isinstance(entity.get(field), dict):
        return entity[field]
    hits = [cfg[field] for cfg in entity.values()
            if isinstance(cfg, dict) and field in cfg]
    return hits[0] if len(hits) == 1 else {}


def _attach_field_mask(items, entity, label):
    """Anexa format=mask aos FIELD de items sem function/format.

    Retorna nova lista (string nua não carrega props). Genérico.
    """
    from ajsystem.defs.report import parse_report_item as _pri
    if not isinstance(items, list):
        return items
    out = []
    for it in items:
        try:
            _ri = _pri(it, label)
        except ValueError:
            out.append(it)
            continue
        if _ri.kind != 'FIELD' or _ri.config.get('function') or _ri.config.get('format'):
            out.append(it)
            continue
        # máscara do field: config (Entity/Schema/query) + override do report.
        _fcfg = _raw_cfg_of(_ri.name, entity)
        if _ri.config.get('mask'):
            _fcfg = {**_fcfg, 'mask': _ri.config['mask']}
        _mask = _field_mask(_ri.name, _fcfg)
        if not _mask:
            out.append(it)
            continue
        _cfg = dict(_ri.config)
        _cfg['format'] = _mask
        out.append({'field': _ri.name, **_cfg})
    return out


def _attach_text_opts(items, entity, label):
    """Anexa _fmt_opts aos TEXT de uma lista de items (in-place, genérico)."""
    from ajsystem.defs.report import parse_report_item as _pri
    for it in items or []:
        try:
            _ri = _pri(it, label)
        except ValueError:
            continue
        if _ri.kind == 'TEXT' and isinstance(_ri.config.get('text'), str):
            _fo = _fmt_opts_for(_ri.config['text'], entity)
            if _fo:
                _ri.config.setdefault('_fmt_opts', _fo)


def _cell_text_fn(tpl, entity):
    """Monta function(row) a partir de template (código montado). Delegado ao
    avaliador único (core/text); labels LIST via options da Entity."""
    import re as _re
    from ajsystem.core.text import render as _render
    _fmt_opts = {}
    for nm in set(_re.findall(r'{(\w+)(?::[^}]*)?}', tpl or '')):
        mdl = None
        if entity and nm in entity and isinstance(entity.get(nm), dict):
            mdl = nm
        else:
            hits = [m for m, cfg in (entity or {}).items()
                    if isinstance(cfg, dict) and nm in cfg] if entity else []
            mdl = hits[0] if len(hits) == 1 else None
        if mdl:
            raw_cfg = entity[mdl] if mdl == nm else entity[mdl].get(nm, {})
            opts = raw_cfg.get('list') or raw_cfg.get('options')
            if opts:
                _fmt_opts[nm] = opts

    def _fn(row):
        from ajsystem.core.text import dotted_get as _dg
        return _render(tpl, lambda k: _dg(row, k), _fmt_opts)
    return _fn


def _mark_suppress(table, cname):
    """Marca suppress na cfg da coluna (dict ou lista), p/ place=0."""
    cols = table.get('columns')
    if isinstance(cols, dict) and isinstance(cols.get(cname), dict):
        cols[cname]['suppress'] = True
    elif isinstance(cols, list):
        for it in cols:
            if isinstance(it, dict) and len(it) == 1 and cname in it:
                cfg = it[cname]
                if isinstance(cfg, dict):
                    cfg['suppress'] = True
                else:
                    it[cname] = {'suppress': True}


def _translate_legacy_group(g, cname, label):
    """Shim: {print, place} legado -> eixos {action, print}.

    print:0/place:0 = coluna normal; print:1/place:0 = abre/suprime;
    place:1 = antes da tabela; place:2 = na linha; print:2 = fecha/total.
    Com 'action' presente, 'place' é erro (escolher um vocabulário).
    """
    g = dict(g)
    if 'action' in g:
        if 'place' in g:
            raise ValueError(f"report '{label}': '{cname}' mistura action e place (escolha um)")
        return g
    pr, pl = g.pop('print', 0), g.pop('place', 0)
    if (pr, pl) == (0, 0):
        return g  # coluna normal
    if pr == 1 and pl == 0:
        g['action'], g['print'] = 1, 1
    elif pr == 1 and pl == 1:
        g['action'], g['print'] = 1, 3
    elif pr == 1 and pl == 2:
        g['action'], g['print'] = 1, 2
    elif pr == 2:
        g['action'], g['print'] = 2, 2
    else:
        raise ValueError(f"report '{label}': print/place de '{cname}' inválido")
    return g


def _synthesize_levels_from_groups(table, body, label):
    """Deriva table.levels de table.groups (dict {campo: cfg}, ordem aninhada).

    Eixos: action (quando: 1 abre, 2 fecha, ausente = toda linha) x print
    (onde, relativo ao evento: 0 nunca, 1 na coluna (default), 2 na linha,
    3 antes/depois da tabela). action:2 + print:2 = linha de total após as
    linhas; action:2 + print:1/3 e print 2/3 sem action = fail-fast (fase
    futura). Valida que order abre com as quebras. columns lista só o que
    imprime.
    """
    groups = table.get('groups')
    if not groups or table.get('levels') or table.get('hierarchy'):
        return
    if isinstance(groups, dict):
        items = [(k, v if isinstance(v, dict) else {}) for k, v in groups.items()]
    elif isinstance(groups, list):
        items = []
        for g in groups:
            if not isinstance(g, dict) or 'field' not in g:
                raise ValueError(f"report '{label}': groups exige {{field, ...}}")
            items.append((g['field'], {k: v for k, v in g.items() if k != 'field'}))
    else:
        raise ValueError(f"report '{label}': groups deve ser dict ou lista")
    cols = table.get('columns') or {}
    col_names = set()
    if isinstance(cols, dict):
        col_names = set(cols.keys())
    elif isinstance(cols, list):
        for it in cols:
            if isinstance(it, str):
                col_names.add(it)
            elif isinstance(it, dict) and len(it) == 1:
                col_names.update(it.keys())
    grouped, synth = [], []
    for cname, g in items:
        if not isinstance(g, dict):
            raise ValueError(f"report '{label}': group de '{cname}' deve ser dict")
        g = _translate_legacy_group(g, cname, label)
        ac, pr = g.get('action'), g.get('print', 1)
        if ac not in (None, 1, 2):
            raise ValueError(f"report '{label}': action de '{cname}' deve ser 1|2")
        if pr not in (0, 1, 2, 3):
            raise ValueError(f"report '{label}': print de '{cname}' deve ser 0|1|2|3")
        if ac is None:
            if pr != 1:
                raise ValueError(f"report '{label}': '{cname}' sem action exige print=1")
            continue  # coluna normal, sem quebra
        if ac == 1:
            if pr == 0:
                raise ValueError(f"report '{label}': '{cname}' com action=1 exige print 1|2|3")
            if pr == 1:
                if cname not in col_names:
                    raise ValueError(f"report '{label}': print=1 exige '{cname}' em columns")
                _mark_suppress(table, cname)
                continue
            grouped.append(cname)
            _sp = {cname: {'pos': 2 if pr == 3 else 1,
                           'text': g.get('text', cname),
                           'total': False, 'gline': True}}
            if g.get('totals') is not None:
                if not isinstance(g['totals'], dict):
                    raise ValueError(f"report '{label}': totals de '{cname}' deve ser dict")
                _sp[cname]['totals'] = g['totals']
            synth.append(_sp)
        else:  # ac == 2 fecha
            if pr == 1:
                raise ValueError(f"report '{label}': action=2/print=1 não suportado nesta fase")
            if pr == 3:
                raise ValueError(f"report '{label}': action=2/print=3 não suportado nesta fase")
            grouped.append(cname)
            synth.append({cname: {'pos': 0, 'total': bool(g.get('total', True)),
                                  'gline': True, 'footer_text': g.get('text', 'Total')}})
    # order da fonte tem que abrir com as colunas de quebra (senão picota)
    src = (body or {}).get('source') if isinstance(body, dict) else None
    if isinstance(src, dict) and src.get('order') and grouped:
        _ord = [o.split()[0] if isinstance(o, str) else (o.get('field') or '') for o in src['order']]
        _ord = [o for o in _ord if o]
        if grouped != _ord[:len(grouped)]:
            raise ValueError(f"report '{label}': order {src['order']} deve abrir com as quebras {grouped}")
    if synth:
        table['levels'] = synth


def _report_inputs():
    """Camadas de inputs (motor + página), igual a `do_list._camadas_inputs`."""
    try:
        from flask import request, current_app
        from ajsystem.core.utils import module_blueprint
        from ajsystem.defs.inputs import module_inputs
        import importlib as _il
        inputs = current_app.extensions.get('inputs')
        try:
            bp_name = request.blueprint
        except RuntimeError:
            return (inputs, {})
        if not bp_name:
            return (inputs, {})
        bp = current_app.blueprints.get(bp_name)
        mod = _il.import_module(bp.import_name) if bp is not None else None
        try:
            pagina = module_inputs(mod) if mod is not None else {}
        except ImportError:
            pagina = {}
        return (inputs, pagina)
    except Exception:
        return (None, {})


def _field_mask(name, cfg):
    """Máscara do campo: a derivação é a do `Field` (tipo/catálogo/decimals) e a
    cfg (Entity/Schema/query/report) vence por cima. O separador de milhar é
    aplicado na renderização. Falha -> None.

    `resolve_field_mask` é genérico — a materialização do `Field` que a versão
    anterior fazia aqui era o custo de não existir uma pergunta genérica.
    """
    if not isinstance(cfg, dict):
        return None
    try:
        from ajsystem.defs.data import resolve_field_mask
        _tipos, _pagina = _report_inputs()
        _camadas = tuple(c for c in (_tipos, _pagina) if c)
        return resolve_field_mask(name, cfg, inputs=_camadas or None)
    except Exception:
        return None


def _entity_cfg_for(entity, entity_name):
    """ cfg flat {campo: cfg} p/ cast tipado (INT/LIST->int). Genérico."""
    if not entity:
        base = _entity_for(entity_name) if isinstance(entity_name, str) else None
        return base or {}
    if isinstance(entity, dict) and entity_name in entity and isinstance(entity[entity_name], dict):
        return entity[entity_name]
    if isinstance(entity, dict) and all(isinstance(v, dict) for v in entity.values()):
        # flat ({campo: cfg}) ou aninhado de 1 nível: usa como está se parecer campo
        return entity
    return {}


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

    # Fonte nova: query dict {select, dist, from, ...} (QPLANO) -> qrun genérico.
    # Índice global estável: numera tudo, filtra depois (filtro funde por cima).
    # levels mora no body do relatório (apresentação), não na query.
    from ajsystem.defs.qspec import is_query_dict
    _src_raw = _source_of(report)
    if isinstance(_src_raw, dict) and is_query_dict(_src_raw):
        from ajsystem.core.list import _resolve_model as _rm
        from ajsystem.core.qrun import run_query, build_levels
        _ent = _module_entity(report)
        _ename = _src_raw.get('from')
        _model = _rm(_ename if isinstance(_ename, str) else None)
        _cfg = _entity_cfg_for(_ent, _ename)
        _rows = run_query(_model, _src_raw, entity_cfg=_cfg, extra_where=filtro)
        _body = _body_of(report)
        _lvl = None
        if isinstance(_body, dict):
            _lvl = _body.get('levels')
        elif _body is not None:
            _lvl = getattr(_body, 'levels', None)
        if _lvl:
            if not isinstance(_lvl, dict):
                raise TypeError("body.levels deve ser dict")
            _rows = build_levels(_rows, pk=_lvl.get('pk', 'id'),
                                 parent=_lvl.get('parent', 'pai_id'),
                                 rn_attr=_lvl.get('using', 'rn'),
                                 group=_lvl.get('group', 'tipo'),
                                 root_fmt=_lvl.get('root', '{g:02d}.{rn:02d}'),
                                 child_fmt=_lvl.get('child', '{parent}.{rn:02d}'),
                                 target=_lvl.get('target', 'indice'),
                                 max_depth=int(_lvl.get('maxdepth', 20)))
        return _rows

    info = _infer_source(report, _module_entity(report))
    name = info['name']
    if not name:
        return None
    from ajsystem.core.list import _resolve_model
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
    from ajsystem.core.qrun import _cast_value
    try:
        _cfg = _entity_cfg_for(_module_entity(report), getattr(model, '__name__', None))
    except Exception:
        _cfg = {}
    for campo, valor in (filtro or {}).items():
        if valor is None or valor == '':
            continue
        col = getattr(model, campo, None)
        if col is not None:
            query = query.filter(col == _cast_value(_cfg.get(campo, {}), valor))
    return query


def print_report_page(report, instance=None, data=None, msg=None, filter=None):
    """Retorna página completa com iframe do PDF embutido (data URI)."""
    report = parse_report(_apply_entity(report, _module_entity(report)))
    data = _auto_data(report, data, instance, filter)
    try:
        from ajsystem.defs.report import PRINT_TEMPLATE
        src = _data_uri(_pdf_bytes(report, data, instance))
        return render_template(PRINT_TEMPLATE, pdf_url=src)
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
            return render_template(OVERLAY_TEMPLATE, pdf_url=src)
        except Exception:
            return _print_erro(msg)
    report = parse_report(_apply_entity(report, _module_entity(report)))
    data = _auto_data(report, data, instance, filter)
    try:
        src = _data_uri(_pdf_bytes(report, data, instance))
        return render_template(OVERLAY_TEMPLATE, pdf_url=src)
    except Exception:
        return _print_erro(msg)


def _field_cfg(entity, field):
    """Config de um campo dentro de uma Entity (flat ou aninhada).

    Entity flat (`{campo: cfg}`) → a própria entrada; Entity aninhada
    (`{Model: {campo: cfg}}`) → busca dentro de cada modelo. `None` se
    ausente ou ambígua.
    """
    if not entity:
        return None
    if field in entity and isinstance(entity.get(field), dict):
        return entity[field]
    hits = [cfg[field] for cfg in entity.values()
            if isinstance(cfg, dict) and field in cfg]
    return hits[0] if len(hits) == 1 else None


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
    cfg = _field_cfg(entity, fs.field)
    if cfg:
        options = cfg.get('options') or cfg.get('list') or {}
        label = cfg.get('label') or label
    rid = uuid.uuid4().hex[:12]
    _PENDING_PRINTS[rid] = {'report': report, 'field': fs.field}
    title = report.get('label') if isinstance(report, dict) else i18n.PRINT
    return choice_modal(
        title=title,
        label=label,
        options=options,
        param=fs.field,
        confirm_label=i18n.PRINT,
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
        from ajsystem.core.pdf import gerar_pdf_relatorio
        return gerar_pdf_relatorio(report, data, _resolve_logo(report), instance=instance)
    raw = _pdf_bytes(report, data, instance)
    return Response(
        raw,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"},
    )


def choice_modal(title, options, param='tipo', label=None,
                 confirm_label=None, hidden_params=None, url_target=None):
    """Modal genérico de escolha (fragmento injetado via reportRender).

    Devoluível por qualquer action de botão: aberto ao injetar; um `<select>`
    com `options` ({valor: rótulo}) + opção implícita vazia (que o filtro
    trata como "Todos"). Ao escolher, o form faz GET para `url_target` (padrão:
    a URL atual) com `?<param>=<valor>` + `hidden_params`.

    Como o submit re-renderiza a própria página, a função da Page deve, no
    render seguinte, detectar `request.args.get('param')` e gerar o relatório.
    Default de `url_target` é `request.path` (sem query) — os parâmetros vêm do
    próprio form (select + hiddens), evitando arrastar query antiga da URL.

    `label`/`confirm_label` são `None` por padrão e resolvidos aqui, não no
    `def`: default de argumento é avaliado uma vez, na importação, o que
    congelaria o texto no locale daquele momento. Um chamador que já tem texto
    pronto (ex.: `i18n.PRINT`) só precisa repassá-lo.
    """
    label = label if label is not None else i18n.CHOOSE
    confirm_label = confirm_label if confirm_label is not None else i18n.OK
    url = url_target or getattr(request, 'choice_url_target', None) or request.path
    return render_template(
        'components/choice_modal.html',
        uid=uuid.uuid4().hex[:8],
        title=title,
        label=label,
        options=options,
        param=param,
        confirm_label=confirm_label,
        all_label=i18n.FILTER_ALL,
        cancel_label=i18n.CANCEL,
        url_target=url,
        hidden_params=(hidden_params or {}),
    )
