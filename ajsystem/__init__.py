import re
from flask import Blueprint, jsonify, request, render_template, url_for
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
    pagina = request.args.get('pagina', '')
    return render_template('pages/construcao.html', pagina=pagina)


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
        return jsonify(error='parâmetro page inválido'), 400
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
    btns = resolve_buttons(lista.get('buttons'), bp_name)
    if btn_idx < 0 or btn_idx >= len(btns):
        return jsonify(error='botão inválido'), 400
    btn = btns[btn_idx]
    # O modal (filter_select) usa `request.path` como url_target por padrão;
    # aqui o path é /ajsystem/list-action, então apontamos para a listagem real.
    try:
        request.choice_url_target = url_for(f'{bp_name}.list')
    except Exception:
        pass
    instance = None
    if instance_id and btn.action:
        entity = None
        for a in dir(mod):
            obj = getattr(mod, a, None)
            if hasattr(obj, 'query'):
                entity = obj
                break
        if entity:
            instance = entity.query.get(instance_id)
    html = btn.action(instance) if btn.action else ''
    return jsonify(html=html or '')


from ajsystem.init import init_app  # noqa: E402  (wiring do framework)
