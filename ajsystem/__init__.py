import re
from flask import (Blueprint, current_app, jsonify, request, render_template,
                   url_for)
from markupsafe import Markup
from flask_login import login_required

ajsystem = Blueprint('ajsystem', __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/ajsystem')


@ajsystem.app_template_filter('heroicon')
def heroicon_filter(name, class_='w-5 h-5'):
    return Markup(
        f'<svg class="{class_}" aria-hidden="true">'
        f'<use href="#i-{name}"/></svg>'
    )


@ajsystem.route('/construcao')
@login_required
def construcao():
    page = request.args.get('pagina', '')
    return render_template('pages/construcao.html', pagina=page)


@ajsystem.route('/api/tunnel-url')
@login_required
def tunnel_url():
    """URL pública atual do túnel (para o QR code)."""
    from ajsystem.core.adapter import get_tunnel_url
    return jsonify(url=get_tunnel_url() or '')


@ajsystem.route('/lookup-search')
@login_required
def lookup_search():
    """JSON de busca declarada p/ modal de lookup (`Lookup.query`).

    `?page=<slug>&query=<NOME>[&<param>=<valor>...]` — importa
    `app.routes.sys.<slug>`, lê a declaração e executa via `core.search`.
    Slug/nome restritos a `[A-Za-z0-9_]` (sem import arbitrário).
    """
    import importlib
    page = request.args.get('page', '') or ''
    name = request.args.get('query', '') or ''
    if not re.fullmatch(r'[A-Za-z0-9_]+', page) or not re.fullmatch(r'[A-Za-z0-9_]+', name):
        return jsonify(error='parâmetros inválidos'), 400
    try:
        from ajsystem.core.adapter import ROUTES_BASE
        mod = importlib.import_module(f'{ROUTES_BASE}.sys.{page}')
    except ImportError:
        return jsonify(error='página desconhecida'), 404
    spec = getattr(mod, name, None)
    if not isinstance(spec, dict):
        return jsonify(error='busca desconhecida'), 404
    from ajsystem.core import search as _search
    params = {k: v for k, v in request.args.items() if k not in ('page', 'query')}
    return jsonify(_search.run_search(spec, params))


@ajsystem.route('/list-action')
@login_required
def list_action():
    """Gera HTML fresco de ação de botão de listagem (via fetch).

    Resolve a action do botão e retorna o HTML (ex.: modal de escolha de
    impressão com rid novo), evitando caching do template estático.
    Parâmetros: page (slug), btn (índice do botão), id (opcional, instance).
    """
    import importlib
    from flask import Blueprint as _BP
    from ajsystem.defs.data import module_page, page_list_cfg

    page = request.args.get('page', '')
    btn_idx = request.args.get('btn', type=int)
    instance_id = request.args.get('id', type=int)
    if not page or btn_idx is None:
        return jsonify(error='parâmetros inválidos'), 400
    if not re.fullmatch(r'[A-Za-z0-9_]+', page):
        return jsonify(error='parâmetro de página inválido'), 400
    try:
        from ajsystem.core.adapter import ROUTES_BASE
        mod = importlib.import_module(f'{ROUTES_BASE}.sys.{page}')
    except ImportError:
        return jsonify(error='página desconhecida'), 404
    page_spec = module_page(mod)
    lista = page_list_cfg(page_spec)
    bp = next((getattr(mod, a) for a in dir(mod)
                if isinstance(getattr(mod, a, None), _BP)), None)
    bp_name = bp.name if bp else None
    from ajsystem.defs.buttons import resolve_buttons
    # As MESMAS camadas que `do_list` usou para desenhar a listagem. Sem a do
    # módulo, um botão de listagem declarado no `Buttons` da rota não resolveria
    # aqui — a página desenhava o botão e o clique dava 500.
    from ajsystem.core.do_list import _camadas_botoes
    _app_cat, _page_cat = _camadas_botoes(mod.__name__)
    btns = resolve_buttons(lista.get('buttons'), bp_name, where='list', ctx='list',
                           types=_app_cat, types_page=_page_cat)
    if btn_idx < 0 or btn_idx >= len(btns):
        return jsonify(error='botão inválido'), 400
    btn = btns[btn_idx]
    if btn.render is None:
        return jsonify(error='botão sem `render`'), 400
    # O modal (filter_select) usa `request.path` como url_target por padrão;
    # aqui o path é /ajsystem/list-action, então apontamos para a listagem real.
    try:
        request.choice_url_target = url_for(f'{bp_name}.list')
    except Exception:
        pass
    instance = None
    if instance_id:
        entity = None
        for a in dir(mod):
            obj = getattr(mod, a, None)
            if hasattr(obj, 'query'):
                entity = obj
                break
        if entity:
            instance = entity.query.get(instance_id)
    return jsonify(html=btn.target_html(instance) or '')


@ajsystem.route('/report-action')
@login_required
def report_action():
    """Gera o PDF de uma entrada da aba Relatórios (props.report, §5.6.2).

    Parâmetros: page (slug da rota), rp (slug da entrada) + args dos campos
    declarados em `filter`. O campo vazio ignora a folha; a spec resultante é
    combinada com o `body.filter` do relatório pelo próprio `print_report`.
    Devolve o fragmento do overlay (JSON `{html}`), como `/list-action`.
    """
    import importlib
    from ajsystem.core.adapter import ROUTES_BASE
    from ajsystem.core.auto import _entidade_principal
    from ajsystem.core.do_list import (_resolve_report_entries,
                                       report_filter_from_args)
    from ajsystem.core.do_report import print_report, _print_erro
    from ajsystem.defs.data import module_page
    page = request.args.get('page', '') or ''
    rp = request.args.get('rp', '') or ''
    if not re.fullmatch(r'[A-Za-z0-9_]+', page) or not rp:
        return jsonify(error='parâmetros inválidos'), 400
    try:
        mod = importlib.import_module(f'{ROUTES_BASE}.sys.{page}')
    except ImportError:
        return jsonify(error='página desconhecida'), 404
    entries = _resolve_report_entries(
        module_page(mod), getattr(mod, 'Schema', None) or {},
        mod.__name__, _entidade_principal(mod))
    entry = next((e for e in entries.values() if e['slug'] == rp), None)
    if entry is None:
        return jsonify(html=_print_erro('Relatório não encontrado')), 404
    # Injeta o título da entrada (chave do dicionário) no relatório
    report = dict(entry['report'])
    report['label'] = entry['title']

    # Monta args mesclados com defaults para campos não preenchidos pelo usuário.
    # Assim tanto o spec literal quanto o texto do subtítulo enxergam os valores
    # prévio.
    from werkzeug.datastructures import MultiDict
    _args = MultiDict(request.args)
    for f in entry.get('fields', []):
        default = f.get('default')
        if default is None:
            continue
        name = f['name']
        if f.get('between'):
            suf = ('_from', '_to') if f['type'] == 'date' else ('_val1', '_val2')
            if any((name + s) in _args for s in suf):
                continue  # usuário preencheu pelo menos um lado
        else:
            if name in _args:
                continue  # usuário preencheu
        _spec = _default_to_spec(f, default)
        for _d in _spec:
            for _k, _v in _d.items():
                if isinstance(_v, tuple):
                    _op, _val = _v
                    if _op == '=':
                        _args[_k] = _val
                    else:
                        _args[_k] = _val
                else:
                    _args[_k] = _v

    # Converte os args (mesclados com defaults) em spec literal
    _filter = report_filter_from_args(entry, _args) or []

    # Popula titles[] com label + texto do filter (se informado), para o
    # header do PDF imprimir via TITLE() em ordem.
    # O texto do filter usa o formato legível da tela (ex.: "Vencimento até
    # 20/09/2026"), não o spec cru da query.
    _titles = [entry['title']]
    _filtros = _report_filter_display_text(entry, _args)
    if _filtros:
        _titles.append(" e ".join(_filtros))
    report['titles'] = _titles

    try:
        html = print_report(report,
                            filter=_filter,
                            _printing=True)
    except Exception:
        html = _print_erro()
    return jsonify(html=html)


def _fmt_filter_val(f, v):
    """Formata um valor de filtro para exibição legível."""
    from datetime import date as _date, datetime as _datetime
    if isinstance(v, (_date, _datetime)):
        return v.strftime('%d/%m/%Y')
    if isinstance(v, str):
        try:
            return _date.fromisoformat(v.strip()).strftime('%d/%m/%Y')
        except (TypeError, ValueError):
            return v
    return str(v)


def _report_filter_display_text(entry, args):
    """Textos legíveis dos filtros preenchidos no form da aba Relatórios.

    Exemplo: ['Vencimento até 20/09/2026', 'Conta = 5'].
    Lê os args brutos da request (não o spec), para exibir labels e valores
    como aparecem na tela.
    """
    out = []
    for f in entry['fields']:
        name = f['name']
        if f.get('between'):
            suf = ('_from', '_to') if f['type'] == 'date' else ('_val1', '_val2')
            lo, hi = args.get(name + suf[0]), args.get(name + suf[1])
            if lo and hi:
                out.append(f"{f['label']} de {_fmt_filter_val(f, lo)} até {_fmt_filter_val(f, hi)}")
            elif lo:
                out.append(f"{f['label']} a partir de {_fmt_filter_val(f, lo)}")
            elif hi:
                out.append(f"{f['label']} até {_fmt_filter_val(f, hi)}")
            continue
        if f['type'] == 'checklist':
            vals = [v for v in args.getlist(name) if v]
            if vals:
                out.append(f"{f['label']}: {', '.join(_fmt_filter_val(f, v) for v in vals)}")
            continue
        v = args.get(name)
        if not v:
            continue
        if f['type'] in ('select', 'boolean'):
            out.append(f"{f['label']} = {v}")
        elif f['op'] == '=':
            out.append(f"{f['label']} = {_fmt_filter_val(f, v)}")
        else:
            out.append(f"{f['label']} {f.get('mode_label', f['op'])} {_fmt_filter_val(f, v)}")
    return out


def _fmt_default_val(v):
    """Converte um valor de default para string p/ exibição no input."""
    from datetime import date as _date, datetime as _datetime
    if callable(v):
        v = v()
    if isinstance(v, _datetime):
        return v.strftime('%d/%m/%Y')
    if isinstance(v, _date):
        return v.strftime('%d/%m/%Y')
    return str(v)


def _default_to_spec(f, default):
    """Converte um default de campo em spec literal (gramática compartilhada).

    Retorna lista de dicts no mesmo formato de `report_filter_from_args`:
    - campo simples com op '=':  {nome: valor}
    - campo simples com op != '=': {nome: (op, valor)}
    - between: [{nome_from: ('>=', v1)}, {nome_to: ('<=', v2)}]
    """
    from datetime import date as _date, datetime as _datetime
    op = f.get('op', '=')
    name = f['name']
    out = []

    if f.get('between'):
        suf = ('_from', '_to') if f['type'] == 'date' else ('_val1', '_val2')
        if isinstance(default, (list, tuple)) and len(default) == 2:
            v1, v2 = default
        else:
            v1 = v2 = default
        if v1 is not None:
            s1 = _fmt_default_val(v1)
            out.append({name + suf[0]: (('>=' if op in ('>', '<>') else '='), s1)})
        if v2 is not None:
            s2 = _fmt_default_val(v2)
            out.append({name + suf[1]: (('<=' if op in ('<', '<>') else '='), s2)})
        return out

    s = _fmt_default_val(default)
    if op == '=':
        return [{name: s}]
    return [{name: (op, s)}]


from ajsystem.init import init_app  # noqa: E402  (wiring do framework)
