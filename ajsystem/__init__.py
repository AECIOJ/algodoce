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
    try:
        html = print_report(report,
                            filter=report_filter_from_args(entry, request.args) or None,
                            _printing=True)
    except Exception:
        html = _print_erro()
    return jsonify(html=html)


from ajsystem.init import init_app  # noqa: E402  (wiring do framework)
