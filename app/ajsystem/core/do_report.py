"""Orquestrador de relatórios PDF — dict declarativo → HTML com PDF embutido.

O motor fica em `core/pdf.py` (gerar_pdf_relatorio); este módulo concentra o
glue: gera os bytes do PDF e os entrega como `Response` inline (`do_report`)
ou embutidos em data URI dentro do fragmento/página de impressão
(`print_report` / `print_report_page`).

Fluxo (sem rotas): a action do botão constrói os dados, chama
`print_report(DICT, data=...)` e o HTML retornado é injetado no container.
"""
import base64
import importlib
import os
import re
from io import BytesIO

from flask import Response, current_app, render_template

from app.ajsystem.core.pdf import gerar_pdf_relatorio
from app.ajsystem.core.list import _resolve_cols
from app.ajsystem.defs.fields import _auto_label
from app.ajsystem.defs.report import parse_report

ERRO_MSG_PADRAO = 'Erro na impressão do Relatório'
ERRO_TEMPLATE = 'components/print_erro.html'


def _print_erro(msg=None):
    """View padrão de erro de impressão (fragmento/página interna)."""
    return render_template(ERRO_TEMPLATE, msg=msg or ERRO_MSG_PADRAO)


def _module_entity():
    """Variável Entity do módulo corrente — como List/Form enxergam.

    Descoberta pela dupla padrão do Flask: request.blueprint →
    current_app.blueprints[...].import_name (= caminho do módulo, gravado
    por montar_blueprint). Fora de um request de blueprint → None.
    """
    from flask import request
    try:
        bp_name = request.blueprint
    except RuntimeError:
        return None
    if not bp_name:
        return None
    bp = current_app.blueprints.get(bp_name)
    if bp is None:
        return None
    try:
        mod = importlib.import_module(bp.import_name)
    except ImportError:
        return None
    return getattr(mod, 'Entity', None)


def _resolve_logo(report):
    """Resolve o path absoluto da logo a partir do path relativo do Report."""
    return os.path.join(current_app.root_path, report.logo_path)


def _pdf_bytes(report, data=None, instance=None):
    """Gera os bytes do PDF para um report já resolvido.

    `data` omitido + instance presente → extrai `instance.<data_attr>`.
    """
    if data is None and instance is not None:
        data = getattr(instance, report.data_attr, None)
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
    """Resolve `fields`/`columns` em forma de mapa `nome: extras`.

    `entity` = variável Entity do módulo corrente (via blueprint). Para cada
    chave:
      - presente em 1 model da Entity  → label + apresentação inferida do
        type (`NUM`/currency→brl right, DATA→datetime right, INT→center)
      - presente em vários             → erro (use `'Model.campo'`)
      - ausente (paths `product.nome`, calculados) → extras passam direto;
        exigem `'label'` ou `'function'` para não mascarar typo
    Extras do report sobrepõem. `width` é sempre em **ch** — o motor converte
    para mm pela métrica da fonte. Sem entity (fora de blueprint) nada é
    resolvido. Retorna cópia ajustada; não muta o declarado.
    """
    if not entity:
        return raw
    out = dict(raw)

    def _locate(field):
        hits = [m for m, cfg in entity.items()
                if isinstance(cfg, dict) and field in cfg]
        return hits[0] if len(hits) == 1 else None

    def _infer_presentation(cfg):
        t, inp, cur = cfg.get('type'), cfg.get('input'), cfg.get('currency')
        fmt = align = None
        if cur:
            fmt, align = cur, 'right'
        elif t == 'NUM':
            fmt, align = 'brl', 'right'
        elif t == 'DATA' or inp == 'date':
            fmt, align = 'datetime', 'right'
        elif t == 'INT':
            align = 'center'
        return {'format': fmt, 'align': align}

    def _resolve_map(sec, map_key):
        items = sec.get(map_key)
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
                raw_cfg = entity[model].get(fld, {})
                base = {'label': raw_cfg.get('label') or _auto_label(fld),
                        **_infer_presentation(raw_cfg)}
                spec = {**{k: v for k, v in base.items() if v is not None},
                        **extra}
                # FK → caminho de exibição via relacionamento ('<base>.nome')
                if (raw_cfg.get('type') == 'FK' and 'field' not in spec
                        and key.endswith('_id')):
                    spec['field'] = f'{key[:-3]}.nome'
                # calc da Entity → function(row) quando não informada
                # (str = expressão sobre campos; callable = usa direto)
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

    header = out.get('header')
    if isinstance(header, dict):
        specs = _resolve_map(header, 'fields')
        if specs is not None:
            out['header'] = {**header, 'fields': [
                {'field': k, **v} for k, v in specs.items()]}

    table = out.get('table')
    if isinstance(table, dict):
        specs = _resolve_map(table, 'columns')
        if specs is not None:
            cols = {}
            for key, spec in specs.items():
                spec = dict(spec)
                # 'field' = caminho de dados (ex.: product.nome) → vira a chave
                data_key = spec.pop('field', None) or key
                cols[data_key] = spec
            out['table'] = {**table, 'columns': cols}

    groups = out.get('groups')
    if isinstance(groups, (dict, list)):
        # dict  {campo: opts}            — um grupo por campo
        # lista [{campo: opts}, ...]     — permite N níveis no MESMO campo
        items = (groups.items() if isinstance(groups, dict)
                 else [(k, v) for item in groups for k, v in (item or {}).items()])
        specs = []
        for field, o in items:
            o = dict(o or {})
            sp = {'field': field,
                  'pos': o.pop('pos', 1),          # 0 oculto | 1 linha | 2 titulo
                  'total': o.pop('total', True),   # subtotal do grupo
                  'line': o.pop('line', True),     # linha horizontal ao fechar
                  'eject': o.pop('eject', False)}  # quebra de página
            if 'left' in o:                          # nº de segmentos do código
                sp['left'] = max(1, int(o.pop('left')))
            # demais extras fluem para o engine: fields/skip/transform/bold
            sp.update(o)
            model = _locate(field)
            if model:
                raw_cfg = entity[model].get(field, {})
                sp['label'] = raw_cfg.get('label') or _auto_label(field)
                opts = raw_cfg.get('list') or raw_cfg.get('options')
                if opts:
                    sp['options'] = opts          # título do grupo = label da option
                if raw_cfg.get('type') == 'FK':
                    # título do grupo via relacionamento (ex.: pai.nome)
                    sp['fk_path'] = f'{field[:-3] if field.endswith("_id") else field}.nome'
            else:
                sp['label'] = o.pop('label', _auto_label(field))
            # extras declarativos fluem inteiros p/ o engine de grupos:
            # fields/skip/transform/bold/text/...
            sp.update(o)
            # 'text': template com {campo} — resolve options (LIST) p/ label
            ttxt = sp.get('text')
            if ttxt:
                import re as _re
                fo = {}
                for nm in set(_re.findall(r'{(\w+)}', ttxt)):
                    mdl = _locate(nm)
                    if mdl:
                        o_ = entity[mdl].get(nm, {})
                        lst = o_.get('list') or o_.get('options')
                        if lst:
                            fo[nm] = lst
                if fo:
                    sp['_fmt_opts'] = fo
            specs.append(sp)
        out['groups'] = specs
    return out


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


def _infer_source(report, entity):
    """Model da Entity que contém TODAS as colunas da tabela.

    Retorna (model_name | None, sort_fn | None, code_cfg | None,
    code_attr) — sort_fn é o `calc` callable de uma das colunas;
    code_cfg/code_attr indicam Field.code (código hierárquico DFS).
    Zero ou múltiplos candidatos → KeyError com orientação.
    """
    tbl = report.table if isinstance(report.table, dict) else None
    items = tbl.get('columns') if tbl else None
    if not entity or not isinstance(items, dict) or not items:
        return None, None, None, None
    bases = [k.split('.')[-1] for k in items]
    cands = [m for m, cfg in entity.items()
             if isinstance(cfg, dict) and all(b in cfg for b in bases)]
    if len(cands) > 1:
        raise KeyError(
            f"Colunas {bases} existem em múltiplos models "
            f"({', '.join(cands)}) — ajuste a declaração "
            f"(report '{report.label}')")
    if not cands:
        raise KeyError(
            f"Nenhum model da Entity contém todas as colunas {bases} "
            f"(report '{report.label}')")
    m = cands[0]
    for b in bases:
        raw = entity[m].get(b, {})
        cc = raw.get('calc')
        if callable(cc):
            return m, cc, None, None
        if isinstance(raw.get('code'), dict):
            return m, None, raw['code'], b
    return m, None, None, None


def _auto_data(report, data, instance):
    """Precedência: `data` explícito → `instance.<data_attr>` →
    inferência pela Entity. Field.code → DFS (hier.codigos);
    calc callable → sort python-side."""
    if data is not None or instance is not None:
        if data is None and instance is not None:
            data = getattr(instance, report.data_attr, None)
        return data
    name, sort_fn, code_cfg, code_attr = _infer_source(
        report, _module_entity())
    if not name:
        return None
    from app.ajsystem.core.list import _resolve_model
    out = list(_resolve_model(name).query.all())
    if code_cfg and code_attr:
        from app.ajsystem.core.hier import codigos
        return codigos(out, attr=code_attr, **code_cfg)
    return sorted(out, key=sort_fn) if (sort_fn and out) else out


def print_report_page(report, instance=None, data=None, msg=None):
    """Retorna página completa com iframe do PDF embutido (data URI).

    Fields/columns resolvem da Entity do módulo corrente
    automaticamente (pegada List/Form). Falha de geração → view padrão
    `print_erro.html` com `msg` (default: 'Erro na impressão do Relatório').
    """
    report = parse_report(_apply_entity(report, _module_entity()))
    data = _auto_data(report, data, instance)
    try:
        src = _data_uri(_pdf_bytes(report, data, instance))
        return render_template(report.print_template, pdf_url=src)
    except Exception:
        return _print_erro(msg)


def print_report(report, instance=None, data=None, msg=None):
    """Retorna fragmento HTML com iframe do PDF embutido (data URI).

    Contrato para uso em botões (`action`): recebe o dict do relatório,
    os dados já construídos pelo app e retorna o fragmento; string vazia
    não injeta nada. Fields/columns resolvem da Entity do
    módulo corrente automaticamente (pegada List/Form).
    Falha → view padrão `print_erro.html` com `msg`.
    """
    report = parse_report(_apply_entity(report, _module_entity()))
    data = _auto_data(report, data, instance)
    try:
        src = _data_uri(_pdf_bytes(report, data, instance))
        return render_template(report.print_fragment_template, pdf_url=src)
    except Exception:
        return _print_erro(msg)
